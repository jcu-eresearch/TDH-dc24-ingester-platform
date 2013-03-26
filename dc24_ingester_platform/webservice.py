"""
Management Service XMLRPC server

Created on Oct 3, 2012

@author: Nigel Sim <nigel.sim@coastalcoms.com>
"""

from twisted.web import xmlrpc
import logging
import os
import sys
import shutil
from twisted.web.resource import Resource
from jcudc24ingesterapi.ingester_platform_api import Marshaller
import traceback
from jcudc24ingesterapi.ingester_exceptions import IngestPlatformError

logger = logging.getLogger(__name__)

def translate_exception(e):
    """Translate an IngestPlatformError into an XMLRPC Fault"""
    code = type(e).__xmlrpc_error__
    msg = str(e)
    return xmlrpc.Fault(code, msg)

class ManagementService(xmlrpc.XMLRPC):
    """
    An example object to be published.
    """
    def __init__(self, staging_dir, service):
        """Initialise the management service. 
        :param service: Service Facade instance being exposed by this XMLRPC service
        """
        xmlrpc.XMLRPC.__init__(self, allowNone=True)
        self.service = service
        self.transaction_counter = 0
        if not os.path.exists(staging_dir):
            raise ValueError("The provided staging directory doesn't exist")
        self.transactions = {}
        self.staging_dir = staging_dir
        self._marshaller = Marshaller()
        
    def xmlrpc_insert(self, obj):
        """ Insert the passed object into the ingester platform
        """
        try:
            return self._marshaller.obj_to_dict(self.service.persist(self._marshaller.dict_to_obj(obj)))
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)
        except Exception, e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_tb(exc_traceback)
            raise xmlrpc.Fault(1, str(e))
 
        
    def xmlrpc_update(self, obj):
        """Store the passed object.
        """
        try:
            return self._marshaller.obj_to_dict(self.service.persist(self._marshaller.dict_to_obj(obj)))
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)
        
    def xmlrpc_precommit(self, unit):
        """Creates a staging area for a unit of work and returns the transaction ID
        """
        try:
            unit = self._marshaller.dict_to_obj(unit)
            # Fix me, this is a possible race condition in a multithreaded env
            transaction_id = self.transaction_counter
            cwd = os.path.join(self.staging_dir, str(transaction_id))
            if not os.path.exists(cwd):
                os.mkdir(cwd)
                
            self.transaction_counter += 1
            self.transactions[transaction_id] = cwd, unit
            return transaction_id
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)

    def xmlrpc_commit(self, transaction_id):
        """Commits a unit of work based on the transaction ID.
        """
        try:
            cwd, unit = self.transactions[int(transaction_id)]
            ret = self._marshaller.obj_to_dict(self.service.commit(unit, cwd), special_attrs=["correlationid"])
            return ret
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)
        finally:
            self.cleanup_transaction(transaction_id)

    def xmlrpc_search(self, object_type, criteria):
        try:
            return self._marshaller.obj_to_dict(self.service.search(object_type, criteria))
        except Exception, e:
            raise xmlrpc.Fault(1, str(e))

    def xmlrpc_getIngesterLogs(self, dataset_id):
        try:
            return self._marshaller.obj_to_dict(self.service.get_ingester_logs(dataset_id))
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)

    def xmlrpc_getRegion(self, region_id):
        """Retrieve a location by id
        """
        try:
            return self._marshaller.obj_to_dict(self.service.get_region(region_id))
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)

    def xmlrpc_getLocation(self, location_id):
        """Retrieve a location by id
        """
        try:
            return self._marshaller.obj_to_dict(self.service.get_location(location_id))
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)

    def xmlrpc_getSchema(self, schema_id):
        """Retrieve a schema by id
        """
        try:
            return self._marshaller.obj_to_dict(self.service.get_schema(schema_id))
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)
        
    def xmlrpc_getDataset(self, dataset_id):
        """Retrieve a dataset by id
        """
        try:
            return self._marshaller.obj_to_dict(self.service.get_dataset(dataset_id))
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)
        
    def xmlrpc_getDataEntry(self, dataset_id, data_entry_id):
        """Retrieve a data entry by dataset id + data entry id
        """
        try:
            return self._marshaller.obj_to_dict(self.service.get_data_entry(dataset_id, data_entry_id))
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)

    def xmlrpc_enableDataset(self, dataset_id):
        """Enable ingestion of a dataset.
        """
        try:
            return self.service.enable_dataset(dataset_id)
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)

    def xmlrpc_disableDataset(self, dataset_id):
        """Disable ingestion of a dataset.
        """
        try:
            return self.service.disable_dataset(dataset_id)
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)
        
    def xmlrpc_findDatasets(self, search_args):
        """Disable ingestion of a dataset.
        """
        try:
            return self._marshaller.obj_to_dict(self.service.find_datasets(**search_args))
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)
        
    def xmlrpc_invokeIngester(self, dataset_id):
        """Disable ingestion of a dataset.
        """
        try:
            return self.service.invoke_ingester(dataset_id)
        except ValueError, e:
            raise xmlrpc.Fault(99, str(e))
        except IngestPlatformError, e:
            raise translate_exception(e)
        
    def xmlrpc_ping(self):
        """A simple connection diagnostic method.
        """
        return "PONG"
        
    def xmlrpc_fault(self):
        """
        Raise a Fault indicating that the procedure should not be used.
        """
        raise xmlrpc.Fault(123, "The fault procedure is faulty.")
    
    def cleanup_transaction(self, transaction_id):
        """Clean up all transaction files"""
        shutil.rmtree(self.transactions[transaction_id][0])
        del self.transactions[transaction_id]
        

class ResettableManagementService(ManagementService):
    def __init__(self, *args, **kwargs):
        ManagementService.__init__(self, *args, **kwargs)

    def xmlrpc_reset(self):
        """Cleans out all data. Used only for testing
        """
        self.service.reset()

class DataController(Resource):
    isLeaf = True

    def __init__(self, service, xmlrpc):
        Resource.__init__(self)
        self.service = service
        self.xmlrpc = xmlrpc

    def render_HEAD(self, request):
        if len(request.postpath) == 0:
            return self.xmlrpc.render_HEAD(request)
        else:
            return Resource.render_HEAD(self, request)

    def render_POST(self, request):
        """On post get the ingest key from the path.
        Then, store the post body for ingest.
        """
        # If this is the root then dispatch to the XMLRPC server
        if len(request.postpath) == 0:
            return self.xmlrpc.render_POST(request)
        
        if len(request.postpath) != 3:
            request.setResponseCode(400)
            return "Invalid request"
        transaction_id = request.postpath[0]
        obj_id = request.postpath[1] # <object class>-<object id>
        attr = request.postpath[2]
        
        class_, oid = obj_id.split(":")
        
        obj_id_path = "%s-%s"%(class_, oid)
        
        if not int(transaction_id) in self.xmlrpc.transactions:
            request.setResponseCode(400)
            return "Transaction not found"
        
        transaction_path, unit = self.xmlrpc.transactions[int(transaction_id)]
        obj_path = os.path.join(transaction_path, obj_id_path)
        if not os.path.exists(obj_path):
            os.mkdir(obj_path)
        attr_rel_path = os.path.join(obj_id_path, attr)
        attr_path = os.path.join(obj_path, attr)
        with open(attr_path, "wb") as f:
            shutil.copyfileobj(request.content, f)
        
        # Update the path
        done = False
        for sets in ["to_update", "to_insert"]:
            for item in getattr(unit,sets):
                if class_ == item.__xmlrpc_class__ and int(oid) == item.id:
                    item[attr].f_path = attr_rel_path
                    done = True
                    break
            if done: break
        return "OK"

def makeServer(staging_dir, service):
    """Construct a management service server using the supplied service facade.
    """
    return DataController(service, ManagementService(staging_dir, service))

def makeResettableServer(staging_dir, service):
    """Construct a management service server using the supplied service facade.
    """
    return DataController(service, ResettableManagementService(staging_dir, service))
