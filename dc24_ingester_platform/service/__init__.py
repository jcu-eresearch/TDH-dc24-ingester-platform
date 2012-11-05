"""This package contains all the service modules. These will be presented as a service
facade, to aggregate all the operations into transactionally safe operations.
"""

class ServiceFacade(object):
    def __init__(self, ingester, repository):
        self.ingester = ingester
        self.repository = repository


class IRepositoryService(object):
    """Interface for data management service
    """
    def persistObservation(self, dataset, time, obs, cwd):
        raise NotImplementedError()

class IIngesterService(object):
    """Interface for ingester service
    """
    def persistDataset(self, dataset):
        raise NotImplementedError()
    def deleteDataset(self, dataset):
        raise NotImplementedError()
    def getDataset(self, id=None):
        raise NotImplementedError()
    def getActiveDatasets(self):
        raise NotImplementedError()
    def persisteSamplerState(self, dataset_id, state):
        raise NotImplementedError()
    def getSamplerState(self, dataset_id):
        raise NotImplementedError()
    def persisteDataSourceState(self, dataset_id, state):
        raise NotImplementedError()
    def getDataSourceState(self, dataset_id):
        raise NotImplementedError()
    def logIngesterEvent(self, dataset_id, timestamp, level, message):
        raise NotImplementedError()
    def getIngesterEvents(self, dataset_id):
        raise NotImplementedError()

def makeService(db_url, repo_url):
    """Construct a service facade from the provided service URLs
    
    If the repo_url is a DAM url construct a DAM repo. If the repo_url is a dict
    then construct a simple local repository
    """
    import ingesterdb
    import repodb
    
    ingester = ingesterdb.IngesterServiceDB(db_url)
    repo = repodb.RepositoryDB(repo_url)
    return ServiceFacade(ingester, repo)