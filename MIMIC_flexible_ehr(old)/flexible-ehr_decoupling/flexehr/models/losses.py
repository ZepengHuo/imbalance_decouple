"""Module containing all binary classification losses."""

import abc
from torch import nn
import torch.nn.functional as F


class BaseLoss(abc.ABC):
    """
    Base class for losses.

    Parameters
    ----------
    record_loss_every: int, optional
        How many steps between each loss record.
    """

    def __init__(self, record_loss_every=1):
        self.n_train_steps = 0
        self.record_loss_every = record_loss_every

    @abc.abstractmethod
    def __call__(self, y_pred, y_true, is_train, storer):
        """Calculates loss for a batch of data."""

    def _pre_call(self, is_train, storer):
        if is_train:
            self.n_train_steps += 1

        if not is_train or self.n_train_steps % self.record_loss_every == 0:
            storer = storer
        else:
            storer = None

        return storer


class BCE(BaseLoss):
    def __init__(self):
        """Compute the binary cross entropy loss."""
        super().__init__()

    def __call__(self, y_pred, y_true, is_train, if_main, storer):
        """Binary cross entropy loss function.

        Parameters
        ----------
        y_pred : torch.Tensor

        y_true : torch.Tensor

        is_trin : bool
            Whether model is training.

        storer: collections.defaultdict
        """
        storer = self._pre_call(is_train, storer)

        loss = F.binary_cross_entropy(y_pred, y_true)

        if storer is not None:
            if is_train:
                storer['train_loss'].append(loss.item())
            else:
                storer['valid_loss'].append(loss.item())

        return loss

    
class BCEWithLogitsLoss(BaseLoss):
    def __init__(self):
        """Compute the binary cross entropy loss."""
        super().__init__()

    def __call__(self, y_pred, y_true, is_train, if_main, storer):
        """Binary cross entropy loss function.

        Parameters
        ----------
        y_pred : torch.Tensor

        y_true : torch.Tensor

        is_trin : bool
            Whether model is training.

        storer: collections.defaultdict
        """
        storer = self._pre_call(is_train, storer)
        
        #criterion = nn.BCEWithLogitsLoss()
        #loss = criterion(y_pred, y_true)
        loss = F.binary_cross_entropy_with_logits(y_pred, y_true)
        
        if storer is not None:
            if is_train:
                storer['train_loss'].append(loss.item())
            else:
                storer['valid_loss'].append(loss.item())

        return loss

class LDAMLoss(nn.Module):
    
    def __init__(self, cls_num_list, max_m=0.5, weight=None, s=30):
        super(LDAMLoss, self).__init__()
        m_list = 1.0 / np.sqrt(np.sqrt(cls_num_list))
        m_list = m_list * (max_m / np.max(m_list))
        m_list = torch.cuda.FloatTensor(m_list)
        self.m_list = m_list
        assert s > 0
        self.s = s
        self.weight = weight

    def forward(self, x, target):
        index = torch.zeros_like(x, dtype=torch.uint8)
        index.scatter_(1, target.data.view(-1, 1), 1)
        
        index_float = index.type(torch.cuda.FloatTensor)
        batch_m = torch.matmul(self.m_list[None, :], index_float.transpose(0,1))
        batch_m = batch_m.view((-1, 1))
        x_m = x - batch_m
    
        output = torch.where(index, x_m, x)
        return F.cross_entropy(self.s*output, target, weight=self.weight)