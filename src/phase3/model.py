"""Small shared encoder Siamese U-Net; eight channels include four validity flags."""
import torch
from torch import nn
import torch.nn.functional as F


def conv(cin, cout):
    return nn.Sequential(nn.Conv2d(cin, cout, 3, padding=1), nn.GroupNorm(1, cout),
                         nn.ReLU(), nn.Conv2d(cout, cout, 3, padding=1), nn.ReLU())


class SiameseUNet(nn.Module):
    def __init__(self, channels=8, width=16):
        super().__init__()
        self.e1, self.e2, self.e3 = conv(channels, width), conv(width, width*2), conv(width*2, width*4)
        self.d2, self.d1 = conv(width*6, width*2), conv(width*3, width)
        self.head = nn.Conv2d(width, 1, 1)

    def encode(self, x):
        a = self.e1(x); b = self.e2(F.max_pool2d(a, 2)); c = self.e3(F.max_pool2d(b, 2))
        return a, b, c

    def forward(self, before, after):
        if before.shape != after.shape or before.ndim != 4 or min(before.shape[-2:]) < 4:
            raise ValueError('Equal NCHW temporal inputs of size >=4 required')
        changes = [torch.abs(a-b) for a, b in zip(self.encode(before), self.encode(after))]
        x = self.d2(torch.cat([F.interpolate(changes[2], size=changes[1].shape[-2:], mode='bilinear', align_corners=False), changes[1]], 1))
        x = self.d1(torch.cat([F.interpolate(x, size=changes[0].shape[-2:], mode='bilinear', align_corners=False), changes[0]], 1))
        return self.head(x)


def masked_loss(logits, target, mask, pos_weight=1.):
    if logits.shape != target.shape or logits.shape != mask.shape:
        raise ValueError('Logit/label/mask shapes must match')
    mask = mask.bool()
    if not mask.any():
        raise ValueError('No valid labeled pixels in batch')
    t, p = target[mask], logits[mask]
    if not torch.isfinite(p).all() or not torch.isfinite(t).all() or not ((t == 0) | (t == 1)).all():
        raise ValueError('Nonfinite logits or nonbinary labels')
    if not 0 < pos_weight <= 20:
        raise ValueError('Positive weight must be in (0,20]')
    return F.binary_cross_entropy_with_logits(p, t, pos_weight=p.new_tensor(pos_weight))
