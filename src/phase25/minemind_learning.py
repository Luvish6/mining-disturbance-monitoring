"""TRAIN-fitted reliability weighting of frozen or temporally trained sensor views."""
import numpy as np
import torch
from src.phase25.minemind import availability


def views(model, x, center, spread):
    z = np.asarray((x-center)/spread, dtype='float32')
    with torch.inference_mode():
        t = torch.from_numpy(z)
        h = np.stack([model.view(t, 1).numpy(), model.view(t, 0).numpy()], 1)
        # Cross-reconstruction disagreement is a proxy, not certified sensor quality.
        e = np.stack([np.mean((model.head(torch.from_numpy(h[:, i])).numpy()[:, j:j+2]-z[:, j:j+2])**2, 1)
                      for i, j in [(0, 2), (1, 0)]], 1)
    return h, e


def fit_reliability(model, before, counts, center, spread):
    if np.ndim(before)!=2 or np.shape(before)[1]!=4 or not len(before) or not availability(before, counts).all():
        raise ValueError('Finite observed TRAIN rows required')
    h, e = views(model, before, center, spread)
    return dict(latent_scale=np.maximum(h.std(0), .05).tolist(),
                residual_scale=np.maximum(np.median(e, 0), .05).tolist(),
                count_scale=np.maximum(np.median(counts, 0), 2).tolist(),
                fitted_rows=len(before), fit_season='TRAIN_BEFORE_ONLY')


def score(model, before, after, counts_before, counts_after, center, spread, state, mode='both'):
    if mode not in ('both', 'sar', 'optical'): raise ValueError('Unknown modality')
    for key, shape in [('latent_scale',(2,8)),('residual_scale',(2,)),('count_scale',(2,))]:
        value=np.asarray(state[key])
        if value.shape!=shape or not np.isfinite(value).all() or (value<=0).any():raise ValueError('Invalid TRAIN reliability state')
    observed = availability(before, counts_before) & availability(after, counts_after)
    observed &= np.array([mode != 'optical', mode != 'sar'])
    a = np.where(np.repeat(observed, 2, 1), before, center)
    b = np.where(np.repeat(observed, 2, 1), after, center)
    ha, ea = views(model, a, center, spread); hb, eb = views(model, b, center, spread)
    distance = np.sqrt(np.mean(((hb-ha)/np.asarray(state['latent_scale']))**2, 2))
    counts = np.minimum(counts_before, counts_after)
    quality = np.where(observed, counts/(counts+np.asarray(state['count_scale'])), 0.)
    # Cross-view consistency unavailable with one sensor: do not invent an error.
    residual = (ea+eb)/2/np.asarray(state['residual_scale'])
    quality *= np.where(observed.all(1)[:, None], 1/(1+residual), 1)
    quality = np.nan_to_num(quality)
    weights = np.divide(quality, quality.sum(1, keepdims=True), out=np.zeros_like(quality), where=quality.sum(1, keepdims=True)>0)
    result = (distance*weights).sum(1); result[~observed.any(1)] = np.nan
    return result, weights
