"""Bounded training and explicit held-out inference for a frozen manifest."""
import argparse
import json
import pickle
import random
from pathlib import Path
import numpy as np
import torch
import rasterio
from rasterio.transform import Affine
from sklearn.ensemble import RandomForestClassifier
from . import VERSION
from .data import prepare, read_manifest, fit_stats, normalized, digest, save_json
from .model import SiameseUNet, masked_loss
from .evaluate import shared_evaluation


class Patches(torch.utils.data.Dataset):
    def __init__(self, manifest, split, stats):
        self.root, self.stats = Path(manifest).parent, stats
        self.records = [r for r in read_manifest(manifest)['records'] if r['split'] == split]

    def __len__(self):
        return len(self.records)

    def __getitem__(self, i):
        with np.load(self.root / self.records[i]['path']) as z:
            a, b = normalized(z, self.stats)
            return tuple(torch.from_numpy(x.copy()) for x in (a, b, z['label'][None].astype('float32'), z['mask'][None]))


def setup(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(2)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def new_directory(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    return path


def train(manifest, output, epochs=30, patience=5, batch_size=4, width=16,
          seed=42, device='cpu', synthetic_smoke=False, max_rf_pixels=100000):
    if epochs < 1 or patience < 1 or batch_size < 1 or width < 2 or max_rf_pixels < 2:
        raise ValueError('Invalid training controls')
    m = read_manifest(manifest, require_splits=True)
    if (m['data_kind'] == 'synthetic') != synthetic_smoke:
        raise ValueError('Use --synthetic-smoke only for synthetic fixtures')
    setup(seed)
    if device == 'cuda' and not torch.cuda.is_available():
        device = 'cpu'
    output = new_directory(output)
    stats = fit_stats(manifest)
    model = SiameseUNet(width=width).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(opt, patience=2, factor=.5)
    loaders = {s: torch.utils.data.DataLoader(Patches(manifest, s, stats),
               batch_size=batch_size, shuffle=(s == 'train'), num_workers=0)
               for s in ('train', 'validation')}
    count0, count1 = m['counts']['train']
    weight = float(np.clip(count0/count1, 1, 20))
    metadata = dict(version=VERSION, manifest_sha256=digest(manifest), data_kind=m['data_kind'],
                    seed=seed, stats=stats, width=width, device=device, pos_weight=weight,
                    threshold=.5, threshold_selection='fixed a priori; test unused',
                    torch_version=str(torch.__version__), epochs_requested=epochs,
                    batch_size=batch_size, learning_rate=.001, patience=patience)
    save_json(output / 'run.json', metadata)
    best, stale, history = float('inf'), 0, []
    for epoch in range(epochs):
        row = dict(epoch=epoch+1, lr=opt.param_groups[0]['lr'])
        for split, loader in loaders.items():
            model.train(split == 'train')
            loss_sum, pixels = 0., 0
            for a, b, y, mask in loader:
                a, b, y, mask = [x.to(device) for x in (a, b, y, mask)]
                with torch.set_grad_enabled(split == 'train'):
                    loss = masked_loss(model(a, b), y, mask, weight)
                    if split == 'train':
                        opt.zero_grad(); loss.backward(); opt.step()
                n = int(mask.sum()); loss_sum += loss.item()*n; pixels += n
            if not pixels:
                raise ValueError('Partition has no valid supervised pixels')
            row[split] = loss_sum/pixels
        history.append(row); scheduler.step(row['validation'])
        if row['validation'] < best:
            best, stale = row['validation'], 0
            torch.save(dict(state_dict=model.state_dict(), metadata=metadata), output / 'best.pt')
        else:
            stale += 1
        save_json(output / 'history.json', history)
        if stale >= patience:
            break
    # Training partition only; no test inputs or labels enter model fitting.
    xs, ys = [], []
    for r in m['records']:
        if r['split'] == 'train':
            with np.load(Path(manifest).parent / r['path']) as z:
                xs.append(z['features'][:, z['mask']].T); ys.append(z['label'][z['mask']])
    x, y = np.concatenate(xs), np.concatenate(ys)
    rng = np.random.default_rng(seed)
    if len(y) > max_rf_pixels:
        idx = rng.choice(len(y), max_rf_pixels, replace=False); x, y = x[idx], y[idx]
    if len(np.unique(y)) != 2:
        raise ValueError('RF pixel cap removed a class; increase cap')
    forest = RandomForestClassifier(n_estimators=100, max_depth=16, min_samples_leaf=2,
                                    class_weight='balanced', random_state=seed, n_jobs=1)
    forest.fit(x, y)
    with open(output / 'rf.pkl', 'wb') as stream:
        pickle.dump(dict(model=forest, metadata=metadata, pixels=len(y)), stream)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    for s in ('train', 'validation'):
        ax.plot([r['epoch'] for r in history], [r[s] for r in history], label=s)
    ax.set(xlabel='Epoch', ylabel='Masked weighted BCE', title=f"{m['data_kind']} training history")
    ax.legend(); fig.savefig(output / 'loss.png'); plt.close(fig)
    return metadata


def infer(manifest, run, output, split='test'):
    """Evaluate once after model selection. Only load trusted locally-created runs."""
    m = read_manifest(manifest, require_splits=True)
    run = Path(run)
    meta = json.loads((run / 'run.json').read_text())
    if digest(manifest) != meta['manifest_sha256']:
        raise ValueError('Dataset differs from frozen training manifest')
    checkpoint = torch.load(run / 'best.pt', map_location='cpu', weights_only=True)
    if checkpoint['metadata'] != meta:
        raise ValueError('Checkpoint metadata mismatch')
    with open(run / 'rf.pkl', 'rb') as stream:
        artifact = pickle.load(stream)
    if artifact['metadata'] != meta:
        raise ValueError('RF metadata mismatch')
    model = SiameseUNet(width=meta['width']); model.load_state_dict(checkpoint['state_dict']); model.eval()
    forest = artifact['model']
    output = new_directory(output)
    targets, rf_probs, sn_probs, blocks, ids = [], [], [], [], []
    for r in m['records']:
        if r['split'] != split:
            continue
        with np.load(Path(manifest).parent / r['path']) as z:
            a, b = normalized(z, meta['stats'])
            with torch.no_grad():
                p = model(torch.from_numpy(a)[None], torch.from_numpy(b)[None]).sigmoid()[0, 0].numpy()
            mask = z['mask']
            rf = np.full(mask.shape, np.nan, dtype='float32')
            rf[mask] = forest.predict_proba(z['features'][:, mask].T)[:, list(forest.classes_).index(1)]
            targets.extend(z['label'][mask].tolist()); rf_probs.extend(rf[mask].tolist()); sn_probs.extend(p[mask].tolist())
            blocks.extend([r['block']]*int(mask.sum()))
            ids.extend([f"{r['path']}:{i}" for i in np.flatnonzero(mask)])
            # Probability maps preserve valid imagery beyond labeled support.
            common = z['valid'].all(axis=0)
            rf_map = np.full(mask.shape, np.nan, dtype='float32')
            rf_map[common] = forest.predict_proba(z['features'][:, common].T)[:, list(forest.classes_).index(1)]
            arrays = [np.where(common, p, -9999), np.where(common, rf_map, -9999),
                      np.where(common, p >= .5, -9999), np.where(common, rf_map >= .5, -9999),
                      np.where(z['label'] != 255, z['label'].astype('float32'), -9999), common.astype('float32'),
                      np.where(z['valid'][2], z['before'][2], -9999),
                      np.where(z['valid'][6], z['after'][2], -9999)]
            dest = output / (Path(r['path']).stem + '.tif')
            with rasterio.open(dest, 'w', driver='GTiff', width=p.shape[1], height=p.shape[0], count=8,
                 dtype='float32', crs=m['crs'], transform=Affine(*r['transform']), nodata=-9999) as ds:
                ds.write(np.stack(arrays).astype('float32'))
                ds.descriptions = ('siamese_probability', 'rf_probability', 'siamese_binary', 'rf_binary',
                                   'reference_label', 'common_valid', 'before_NDVI', 'after_NDVI')
                ds.update_tags(data_kind=m['data_kind'], interpretation='mining-related disturbance screening')
    report = shared_evaluation(targets, rf_probs, sn_probs, blocks, meta['threshold'])
    report.update(data_kind=m['data_kind'], manifest_sha256=digest(manifest), partition=split,
                  exclusions=m['quality'], class_counts_by_partition=m['counts'])
    save_json(output / 'evaluation.json', report)
    np.savez_compressed(output / 'common_pixels.npz', ids=ids, label=targets, rf=rf_probs, siamese=sn_probs, blocks=blocks)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2)
    for ax, name in zip(axes, ('rf', 'siamese')):
        cm = np.array(report[name]['confusion_matrix'])
        ax.imshow(cm); ax.set(title=f"{m['data_kind']} {name}", xlabel='Predicted', ylabel='Reference', xticks=[0,1], yticks=[0,1])
        for (i,j), val in np.ndenumerate(cm):
            ax.text(j, i, str(val), ha='center', color='red')
    fig.tight_layout(); fig.savefig(output / 'confusion.png'); plt.close(fig)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('raster'); p.add_argument('labels'); p.add_argument('output')
    p.add_argument('--patch-size', type=int, default=64)
    p.add_argument('--block-m', type=float, default=5000)
    p.add_argument('--buffer-m', type=float, default=120)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--synthetic', action='store_true')
    t = sub.add_parser('train')
    t.add_argument('manifest'); t.add_argument('output')
    t.add_argument('--epochs', type=int, default=30); t.add_argument('--patience', type=int, default=5)
    t.add_argument('--batch-size', type=int, default=4); t.add_argument('--width', type=int, default=16)
    t.add_argument('--seed', type=int, default=42); t.add_argument('--device', choices=['cpu','cuda'], default='cpu')
    t.add_argument('--synthetic-smoke', action='store_true')
    i = sub.add_parser('infer')
    i.add_argument('manifest'); i.add_argument('run'); i.add_argument('output')
    i.add_argument('--split', choices=['validation', 'test'], default='test')
    args = vars(parser.parse_args()); command = args.pop('command')
    {'prepare': prepare, 'train': train, 'infer': infer}[command](**args)


if __name__ == '__main__':
    main()
