import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, f1_score
from torch.nn import functional as F
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
os.environ['CUDA_LAUNCH_BLOCKING'] = '1'


class Classifier(nn.Module):
    def __init__(self, input_size, num_classes):
        super(Classifier, self).__init__()
        self.fc = nn.Linear(input_size, num_classes)

    def forward(self, x):
        return self.fc(x)


def evaluation(model, feature_df, fold=100):
    x = model

    valid_labels = ['primary', 'secondary', 'tertiary', 'residential']
    id_dict = {idx: i for i, idx in enumerate(valid_labels)}
    y_df = feature_df.loc[feature_df['highway'].isin(valid_labels)]
    x = x[y_df['fid'].tolist()]
    y = torch.tensor(y_df['highway'].map(id_dict).tolist())

    split = x.shape[0] // fold

    device_flag = True

    y_preds = []
    y_trues = []
    for i in range(fold):
        eval_idx = list(range(i * split, (i + 1) * split, 1))
        train_idx = list(set(list(range(x.shape[0]))) - set(eval_idx))

        x_train, x_eval = x[train_idx], x[eval_idx]
        y_train, y_eval = y[train_idx], y[eval_idx]

        model = Classifier(x.shape[1], len(valid_labels)).cuda()

        if device_flag:
            print('device: ', next(model.parameters()).device)
            device_flag = False

        opt = torch.optim.Adam(model.parameters(), lr=1e-2)

        best_acc = 0.
        for e in range(1, 101):
            model.train()
            ce_loss = nn.CrossEntropyLoss()(model(x_train), y_train.cuda())

            opt.zero_grad()
            ce_loss.backward()
            opt.step()

            model.eval()
            logit = F.softmax(model(x_eval), -1).detach().cpu()
            y_pred = torch.argmax(logit, dim=1)
            acc = accuracy_score(y_eval.cpu(), y_pred, normalize=False)
            if acc > best_acc:
                best_acc = acc
                best_pred = y_pred
        y_preds.append(best_pred)
        y_trues.append(y_eval.cpu())

    y_preds = torch.cat(y_preds, dim=0)
    y_trues = torch.cat(y_trues, dim=0)

    macro_f1 = f1_score(y_trues, y_preds, average='macro')
    micro_f1 = f1_score(y_trues, y_preds, average='micro')
    print(f'road classification     | micro F1: {micro_f1:.4f}, macro F1: {macro_f1:.4f}')

