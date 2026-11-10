"""Paired common-pixel evaluation, with block rather than pixel uncertainty."""
import numpy as np


def metrics(y, probability, threshold=.5):
    y, probability = np.asarray(y), np.asarray(probability)
    if y.shape != probability.shape or not y.size or not np.isin(y, [0, 1]).all():
        raise ValueError('Nonempty aligned binary targets required')
    if not np.isfinite(probability).all() or ((probability < 0) | (probability > 1)).any() or not 0 <= threshold <= 1:
        raise ValueError('Probabilities/threshold outside [0,1]')
    pred = probability >= threshold
    cm = np.bincount(2*y.astype(int).ravel()+pred.astype(int).ravel(), minlength=4).reshape(2, 2)
    def ratio(a, b):
        return float(a/b) if b else None
    classes = []
    for c in (0, 1):
        tp = cm[c, c]; fp = cm[:, c].sum()-tp; fn = cm[c].sum()-tp
        classes.append(dict(precision=ratio(tp, tp+fp), recall=ratio(tp, tp+fn),
                            f1=ratio(2*tp, 2*tp+fp+fn), iou=ratio(tp, tp+fp+fn),
                            support=int(cm[c].sum())))
    return dict(confusion_matrix=cm.tolist(), classes=classes,
                positive_fraction=float(y.mean()), accuracy=float(np.trace(cm)/cm.sum()),
                threshold=threshold, undefined_metrics='null')


def shared_evaluation(y, rf, siamese, blocks, threshold=.5, seed=42, repeats=200):
    y, rf, siamese, blocks = map(np.asarray, (y, rf, siamese, blocks))
    if not (y.shape == rf.shape == siamese.shape == blocks.shape):
        raise ValueError('Both models must predict the identical ordered common pixel IDs')
    result = dict(rf=metrics(y, rf, threshold), siamese=metrics(y, siamese, threshold))
    unique = np.unique(blocks)
    result['independent_test_blocks'] = len(unique)
    result['per_block'] = {str(b): dict(rf=metrics(y[blocks==b], rf[blocks==b], threshold),
                                       siamese=metrics(y[blocks==b], siamese[blocks==b], threshold)) for b in unique}
    result['uncertainty_warning'] = 'Few independent blocks; intervals are unstable' if len(unique) < 10 else None
    if len(unique) < 2:
        result['paired_f1_difference_95pct'] = None
    else:
        rng, differences = np.random.default_rng(seed), []
        for _ in range(repeats):
            idx = np.concatenate([np.flatnonzero(blocks == b) for b in rng.choice(unique, len(unique), replace=True)])
            a, b = metrics(y[idx], rf[idx], threshold)['classes'][1]['f1'], metrics(y[idx], siamese[idx], threshold)['classes'][1]['f1']
            if a is not None and b is not None:
                differences.append(b-a)
        result['paired_f1_difference_95pct'] = np.percentile(differences, [2.5, 97.5]).tolist() if differences else None
    return result
