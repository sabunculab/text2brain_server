from pathlib import Path
import numpy as np
import pandas as pd


class PaperIndex:
    def __init__(self, image_folder):
        root = Path(image_folder)
        self.mask = np.load(root/'mask.npy')

        frame = pd.read_csv('train.csv', usecols=['article-title', 'article-pmid'], dtype=str)
        frame = frame.sort_values('article-pmid')
        pmid2title = frame.set_index('article-pmid', drop=True).to_dict()['article-title']

        self.haystack = np.zeros((len(frame), self.mask.sum()), dtype=np.float16)
        data_rows = []
        for i, pmid in enumerate(frame['article-pmid']):
            fp = root/f'pmid_{pmid}.npy'
            if not fp.exists():
                raise Exception(f'Image of PMID {pmid} missing')

            data_rows.append({'pmid': pmid, 'title': pmid2title[pmid]})
            self.haystack[i] = self.row_of_voxels(np.load(fp))
        self.ssB = (self.haystack**2).sum(1)

        self.corpus = pd.DataFrame(data_rows)

        print('Initialized')

    def row_of_voxels(self, image):
        assert image.shape == self.mask.shape, f'unexpected image shape {image.shape}'
        out = image[self.mask].astype(np.float16)
        return out - out.mean()

    def corr_coeff(self, A_mA):
        # Sum of squares across rows
        ssA = (A_mA**2).sum(axis=1, keepdims=True)

        # corr coeff
        num = np.dot(A_mA, self.haystack.T)
        den = np.sqrt(np.dot(ssA, self.ssB[None]))
        return np.where(den, num / den, 0)  # return 0 correlation when denominator is 0

    def query(self, image, topk=5):
        needle = self.row_of_voxels(image).reshape(1, -1)
        corr = self.corr_coeff(needle).squeeze()
        indices = np.argsort(corr)[-topk:][::-1]
        # return list of dict with 2 keys 'pmid' and 'title'
        return self.corpus.iloc[indices].to_dict('records')



if __name__ == '__main__':
    librarian = PaperIndex('data/processed/images/')
    out = librarian.query(np.load('data/processed/images/pmid_10523407.npy'))
    print(out)
    assert out[0]['pmid'] == '10523407'
    out = librarian.query(np.load('data/processed/images/pmid_10666559.npy'))
    print(out)
    assert out[0]['pmid'] == '10666559'
