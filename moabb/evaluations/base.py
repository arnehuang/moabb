import logging
import traceback
from abc import ABC, abstractmethod

from sklearn.base import BaseEstimator

from moabb.analysis import Results
from moabb.datasets.base import BaseDataset
from moabb.paradigms.base import BaseParadigm

log = logging.getLogger()


class BaseEvaluation(ABC):
    '''Base class that defines necessary operations for an evaluation.
    Evaluations determine what the train and test sets are and can implement
    additional data preprocessing steps for more complicated algorithms.

    Parameters
    ----------
    paradigm : Paradigm instance
        the paradigm to use.
    datasets : List of Dataset Instance.
        The list of dataset to run the evaluation. If none, the list of
        compatible dataset will be retrieved from the paradigm instance.
    random_state:
        if not None, can guarantee same seed
    n_jobs: 1;
        number of jobs for fitting of pipeline
    overwrite: bool (defaul False)
        if true, overwrite the results.
    suffix: str
        suffix for the results file.
    '''

    def __init__(self, paradigm, datasets=None, random_state=None, n_jobs=1,
                 overwrite=False, suffix=''):
        self.random_state = random_state
        self.n_jobs = n_jobs

        # check paradigm
        if not isinstance(paradigm, BaseParadigm):
            raise(ValueError("paradigm must be an Paradigm instance"))
        self.paradigm = paradigm

        # if no dataset provided, then we get the list from the paradigm
        if datasets is None:
            datasets = self.paradigm.datasets

        if not isinstance(datasets, list):
            if isinstance(datasets, BaseDataset):
                datasets = [datasets]
            else:
                raise(ValueError("datasets must be a list or a dataset "
                                 "instance"))

        for dataset in datasets:
            if not(isinstance(dataset, BaseDataset)):
                raise(ValueError("datasets must only contains dataset "
                                 "instance"))

        for dataset in datasets:
            # fixme, we might want to drop dataset that are not compatible
            try:
                self.paradigm.verify(dataset)
                self.verify(dataset)
            except AssertionError:
                log.warning(f"{dataset} not compatible with evaluation or "
                            "paradigm. Removing this dataset from the list.")
                datasets.remove(dataset)

        self.datasets = datasets

        self.results = Results(type(self),
                               type(self.paradigm),
                               overwrite=overwrite,
                               suffix=suffix)

    def process(self, pipelines):
        '''Runs all pipelines on all datasets.

        This function will apply all provided pipelines and return a dataframe
        containing the results of the evaluation.

        Parameters
        ----------
        pipelines : dict of pipeline instance.
            A dict containing the sklearn pipeline to evaluate.

        Return
        ------
        results: pd.DataFrame
            A dataframe containing the results.

        '''

        # check pipelines
        if not isinstance(pipelines, dict):
            raise(ValueError("pipelines must be a dict"))

        for _, pipeline in pipelines.items():
            if not(isinstance(pipeline, BaseEstimator)):
                raise(ValueError("pipelines must only contains Pipelines "
                                 "instance"))

        for dataset in self.datasets:
            log.info('Processing dataset: {}'.format(dataset.code))
            results = self.evaluate(dataset, pipelines)
            for res in results:
                self.push_result(res, pipelines)

        return self.results.to_dataframe()

    def push_result(self, res, pipelines):
        message = '{} | '.format(res['pipeline'])
        message += '{} | {} | {}'.format(res['dataset'].code,
                                         res['subject'], res['session'])
        message += ': Score %.3f' % res['score']
        log.info(message)
        self.results.add({res['pipeline']: res}, pipelines=pipelines)

    @abstractmethod
    def evaluate(self, dataset, pipelines):
        '''Evaluate results on a single dataset.

        This method return a generator. each results item is a dict with
        the following convension::

            res = {'time': Duration of the training ,
                   'dataset': dataset id,
                   'subject': subject id,
                   'session': session id,
                   'score': score,
                   'n_samples': number of training examples,
                   'n_channels': number of channel,
                   'pipeline': pipeline name}
        '''
        pass

    @abstractmethod
    def verify(self, dataset):
        """Verify the dataset is compatible with evaluation.

        This method is called to verify dataset given in the constructor
        are compatible with the evaluation context.

        This method should raise an error if the dataset is not compatible
        with the evaluation context. This is for example the case if the
        dataset does not contain enought session for a cross-session eval.

        Parameters
        ----------
        dataset : dataset instance
            The dataset to verify.
        """
