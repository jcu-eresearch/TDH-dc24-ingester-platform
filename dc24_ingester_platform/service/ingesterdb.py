"""
Created on Oct 5, 2012

@author: nigel
"""
from dc24_ingester_platform.service import IIngesterService, find_method, method, PersistenceError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, ForeignKey, DateTime
import sqlalchemy.orm as orm
from sqlalchemy.schema import Table
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm.exc import NoResultFound
import decimal
import logging
from dc24_ingester_platform.utils import parse_timestamp

logger = logging.getLogger(__name__)

Base = declarative_base()

def obj_to_dict(obj, klass=None):
    """Maps an object of base class BaseManagementObject to a dict.
    """
    ret = {}
    for attr in dir(obj):
        if attr.startswith("_") or attr == "metadata": continue
        if type(getattr(obj, attr)) in (str, int, float, unicode, dict, bool, type(None)):
            ret[attr] = getattr(obj, attr)
        elif type(getattr(obj, attr)) == decimal.Decimal:
            ret[attr] = float(getattr(obj, attr))
    if klass != None: ret["class"] = klass
    elif hasattr(obj, "__xmlrpc_class__"): ret["class"] = obj.__xmlrpc_class__

    if ret["class"] == "schema":
        ret["class"] = ret["for_"] + "_schema"
        del ret["for_"]
        ret["attributes"] = [{"name":attr.name, "class":attr.kind, "description":attr.description, "units":attr.units} for attr in obj.attributes]
        ret["extends"] = [obj_to_dict(p) for p in obj.extends]
    elif ret["class"] == "region":
        obj.region_points.sort(cmp=lambda a,b: cmp(a.order,b.order))
        ret["region_points"] = [(point.latitude, point.longitude) for point in obj.region_points]
    elif ret["class"] == "dataset":
        if ret["x"] != None:
            ret["location_offset"] = {"class":"offset", "x":ret["x"], 
                                      "y":ret["y"], "z":ret["z"]}
        del ret["x"]
        del ret["y"]
        del ret["z"]
    return ret

def dict_to_object(dic, obj):
    for attr in dir(obj):
        if attr.startswith("_"): continue
        if dic.has_key(attr): setattr(obj, attr, dic[attr])

class Region(Base):
    __tablename__ = "REGION"
    __xmlrpc_class__ = "region"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    #parentRegions = orm.relationship("Region")
    region_points = orm.relationship("RegionPoint")
    
class RegionPoint(Base):
    __tablename__ = "REGION_POINT"
    id = Column(Integer, primary_key=True)
    order = Column(Integer, unique=True)
    latitude = Column(DECIMAL)
    longitude = Column(DECIMAL)
    region_id = Column(Integer, ForeignKey("REGION.id"))
    
    def __init__(self, lat=None, lng=None, order=None):
        self.latitude = lat
        self.longitude = lng
        self.order = order

class Location(Base):
    __tablename__ = "LOCATIONS"
    __xmlrpc_class__ = "location"
    id = Column(Integer, primary_key=True)
    latitude = Column(DECIMAL)
    longitude = Column(DECIMAL)
    name = Column(String)
    elevation = Column(DECIMAL)
    repositoryId = Column(String)
    #region = orm.relationship("Region", uselist=False)

class Dataset(Base):
    __tablename__ = "DATASETS"
    __xmlrpc_class__ = "dataset"
    id = Column(Integer, primary_key=True)
    location = Column(Integer, ForeignKey('LOCATIONS.id'))
    data_source = orm.relationship("DataSource", uselist=False)
    sampling = orm.relationship("Sampling", uselist=False)
    schema = Column(Integer, ForeignKey('SCHEMA.id'))
    enabled = Column(Boolean, default=True)
    description = Column(String)
    redbox_uri = Column(String)
    repositoryId = Column(String)
    # FIXME: Move to separate schema
    x = Column(DECIMAL)
    y = Column(DECIMAL)
    z = Column(DECIMAL)

class Sampling(Base):
    """A DataSource is a generic data storage class"""
    __tablename__ = "SAMPLING"
    __xmlrpc_class__ = "sampling"
    id = Column(Integer, primary_key=True)
    kind = Column(String)
    dataset_id = Column(Integer, ForeignKey("DATASETS.id"))
    parameters = orm.relationship("SamplingParameter")

class SamplingParameter(Base):
    __tablename__ = "SAMPLING_PARAMETERS"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    value = Column(String)
    sampling_id = Column(Integer, ForeignKey("SAMPLING.id"))
    
class DataSource(Base):
    """A DataSource is a generic data storage class"""
    __tablename__ = "DATA_SOURCES"
    __xmlrpc_class__ = "data_source"
    id = Column(Integer, primary_key=True)
    kind = Column(String)
    dataset_id = Column(Integer, ForeignKey("DATASETS.id"))
    parameters = orm.relationship("DataSourceParameter")
    processing_script = Column(String(32000))

class DataSourceParameter(Base):
    __tablename__ = "DATA_SOURCE_PARAMETERS"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    value = Column(String)
    dataset_source_id = Column(Integer, ForeignKey("DATA_SOURCES.id"))
    

schema_to_schema = Table("schema_to_schema", Base.metadata,
    Column("child_id", Integer, ForeignKey("SCHEMA.id"), primary_key=True),
    Column("parent_id", Integer, ForeignKey("SCHEMA.id"), primary_key=True)
)

class Schema(Base):
    __tablename__ = "SCHEMA"
    __xmlrpc_class__ = "schema"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    for_ = Column(String, name="for")
    attributes = orm.relationship("SchemaAttribute")
    repositoryId = Column(String)
    extends = relationship("Schema",
        secondary=schema_to_schema,
        primaryjoin=id==schema_to_schema.c.child_id,
        secondaryjoin=id==schema_to_schema.c.parent_id)
    
class SchemaAttribute(Base):
    __tablename__ = "SCHEMA_ATTRIBUTE"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    kind = Column(String)
    units = Column(String)
    description = Column(String)
    schema_id = Column(Integer, ForeignKey("SCHEMA.id"))

class IngesterLog(Base):
    __tablename__ = "INGESTER_LOG"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    level = Column(String)
    message = Column(String)
    dataset_id = Column(Integer, ForeignKey("DATASETS.id"))

class SamplerState(Base):
    __tablename__ = "SAMPLER_STATE"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    value = Column(String)
    dataset_source_id = Column(Integer, ForeignKey("DATA_SOURCES.id"))
 
class DataSourceState(Base):
    __tablename__ = "DATA_SOURCE_STATE"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    value = Column(String)
    dataset_source_id = Column(Integer, ForeignKey("DATA_SOURCES.id"))   
    
def merge_parameters(col_orig, col_new, klass, name_attr="name", value_attr="value"):
    """This method updates col_orig removing any that aren't in col_new, updating those that are, and adding new ones
    using klass as the constructor
    
    col_new is a dict
    col_orig is a list
    klass is a type
    """
    working = col_new.copy()
    to_del = []
    for obj in col_orig:
        if getattr(obj,name_attr) in working:
            # Update
            setattr(obj, value_attr, working[obj.name])
            del working[obj.name]
        else:
            # Delete pending
            to_del.append(obj)
    # Delete
    for obj in to_del:
        col_orig.remove(obj)
    # Add
    for k in working:
        obj = klass()
        setattr(obj, name_attr, k)
        setattr(obj, value_attr, working[k])
        col_orig.append(obj)
        
def merge_schema_lists(col_orig, col_new):
    """This method updates col_orig removing any that aren't in col_new, updating those that are, and adding new ones
    using klass as the constructor
    
    col_new is a list
    col_orig is a list
    """
    working = dict([(obj.name, obj) for obj in col_new])
    to_del = []
    for obj in col_orig:
        if obj.name in working:
            # Update
            obj.description = working[obj.name].description
            del working[obj.name]
        else:
            # Delete pending
            to_del.append(obj)
    # Delete
    for obj in to_del:
        col_orig.remove(obj)
    # Add
    for k in working:
        col_orig.append(working[k])

def parameters_to_dict(params, name_attr="name", value_attr="value"):
    """Map a parameters set back to a dict"""
    ret = {}
    for obj in params:
        k = getattr(obj, name_attr)
        v = getattr(obj, value_attr)
        ret[k] = v
    return ret
        
def ingest_order(x, y):
    """Sort objects by class according to the order which will make an insert transaction work.
    """
    order = ["_schema", "region", "location", "dataset"]
    x_i = len(order)
    y_i = len(order)
    for i in range(len(order)): 
        if x["class"].endswith(order[i]): 
            x_i = i
            break
    for i in range(len(order)): 
        if y["class"].endswith(order[i]): 
            y_i = i
            break
    return cmp(x_i, y_i)

class IngesterServiceDB(IIngesterService):
    """This service provides DAO operations for the ingester service.
    
    All objects/DTOs passed in and out of this service are dicts. This service protects the storage layer.
    """
    def __init__(self, db_url, repo):
        self.engine = create_engine(db_url)
        Location.metadata.create_all(self.engine, checkfirst=True)
        
        self.samplers = {}
        self.data_source = {}
        self.repo = repo

    def reset(self):
        Location.metadata.drop_all(self.engine)
        Location.metadata.create_all(self.engine, checkfirst=True)
        self.repo.reset()

    def commit(self, unit, cwd):
        """Commit a unit of work with file objects based in cwd"""
        s = orm.sessionmaker(bind=self.engine)()
        ret = []
        locs = {}
        schemas = {}
        datasets = {}
        try:
            unit["insert"].sort(ingest_order)
            unit["update"].sort(ingest_order)
            # delete first
            # now sort to find objects by order of dependency (location then dataset)
            for obj in unit["insert"]:
                oid = obj["id"]
                cls = obj["class"]
                del obj["id"]
                if cls == "dataset":
                    if obj["location"] < 0: obj["location"] = locs[obj["location"]]
                    if obj["schema"] < 0: obj["schema"] = schemas[obj["schema"]]
                elif cls.endswith("schema"):
                    if "extends" in obj:
                        obj["extends"] = [ schemas[p_id] if p_id<0 else p_id for p_id in obj["extends"]]
                    else:
                        obj["extends"] = []
                        
                fn = find_method(self, "persist", cls)
                if fn == None:
                    raise ValueError("Could not find method for", "persist", cls)
                obj = fn(obj, s, cwd)
                if cls == "location":
                    locs[oid] = obj["id"]
                elif cls.endswith("schema"):
                    schemas[oid] = obj["id"]
                        
                obj["correlationid"] = oid
                ret.append(obj)
            s.commit()
            return ret
        finally:
            s.close()

    def persist(self, obj):
        obj = obj.copy()
        
        cls = obj["class"]
        del obj["class"]
        fn = find_method(self, "persist", cls)
        if fn != None:
            s = orm.sessionmaker(bind=self.engine)()
            try:
                obj = fn(obj, s, None)
                s.commit()
                return obj
            finally:
                s.close()
        raise ValueError("%s not supported"%(cls))

    @method("persist", "dataset")
    def persistDataset(self, dataset, session, cwd):
        """Assumes that we have a copy of the object, so we can change it if required.
        """
        if "location" not in dataset:
            raise ValueError("Location must be set")
        # Check schema is of the correct type
        try:
            location = session.query(Location).filter(Location.id == dataset["location"]).one()
        except NoResultFound, e:
            raise ValueError("Provided location not found")
        try:
            schema = session.query(Schema).filter(Schema.id == dataset["schema"]).one()
        except NoResultFound, e:
            raise ValueError("Provided schema not found")
        if schema.for_ != "data_entry":
            raise ValueError("The schema must be for a data_entry")
        
        ds = Dataset()
        data_source = dataset["data_source"].copy() if dataset.has_key("data_source") and dataset["data_source"] != None else None
        sampling = dataset["sampling"].copy() if dataset.has_key("sampling") and dataset["sampling"] != None else None
        if dataset.has_key("data_source"): del dataset["data_source"]
        if dataset.has_key("sampling"): del dataset["sampling"]
        if dataset.has_key("id") and dataset["id"] != None:
            ds = obj_to_dict(session.query(Dataset).filter(Dataset.id == dataset["id"]).one())
 
        dict_to_object(dataset, ds)
        if "location_offset" in dataset and dataset["location_offset"] != None:
            try:
                ds.x = dataset["location_offset"]["x"]
                ds.y = dataset["location_offset"]["y"]
                ds.z = dataset["location_offset"]["z"]
            except:
                raise ValueError("Location offset is invalid")

        # Clean up the sampling link
        if ds.data_source == None and data_source != None:
            ds.data_source = DataSource()
        elif ds.data_source != None and data_source == None:
            del ds.data_source
        # If the sampling object actually exists then populate it
        if ds.data_source != None:
            ds.data_source.kind = data_source["class"]
            del data_source["class"]
            merge_parameters(ds.data_source.parameters, data_source, DataSourceParameter)
        
        # Clean up the sampling link
        if ds.sampling == None and sampling != None:
            ds.sampling = Sampling()
        elif ds.sampling != None and sampling == None:
            del ds.sampling
        # If the sampling object actually exists then populate it
        if ds.sampling != None:
            ds.sampling.kind = sampling["class"]
            del sampling["class"]
            merge_parameters(ds.sampling.parameters, sampling, SamplingParameter)
                
        # If the repo has a method to persist the dataset then call it and record the output
        fn = find_method(self.repo, "persist", "dataset")
        if fn != None:
            ds.repositoryId = fn(ds, schema, location)

        self._persist(ds, session)
        return self._getDataset(ds.id, session)

    @method("persist", "region")    
    def persistRegion(self, region, session, cwd):
        points = region["region_points"]
        del region["region_points"]
        reg = Region()
        if region.has_key("id") and region["id"] != None:
            reg = obj_to_dict(session.query(Region).filter(Region.id == region["id"]).one())
        dict_to_object(region, reg)
        
        while len(reg.region_points) > 0:
            reg.region_points.remove(0)
        i = 0
        for lat,lng in points:
            reg.region_points.append(RegionPoint(lat, lng, i))
            i += 1
        
        return self._persist(reg, session)
    
    @method("persist", "location")    
    def persistLocation(self, location, s, cwd):
        loc = Location()
        dict_to_object(location, loc)
        # If the repo has a method to persist the dataset then call it and record the output
        fn = find_method(self.repo, "persist", "location")
        if fn != None:
            loc.repositoryId = fn(loc)

        return self._persist(loc, s)
    
    @method("persist", "dataset_metadata_schema")
    def persistDatasetMetaDataSchema(self, schema, session, cwd):
        return self._persistSchema(schema, "dataset_metadata", session)

    @method("persist", "data_entry_schema")
    def persistDataEntrySchema(self, schema, session, cwd):
        return self._persistSchema(schema, "data_entry", session)

    @method("persist", "schema")
    def persistGenericSchema(self, schema, session, cwd):
        return self._persistSchema(schema, "schema", session)
        
    def _persistSchema(self, schema, for_, s):
        if "id" in schema and schema["id"] != None:
            raise PersistenceError("Updates are not supported for Schemas")
        
        schema = schema.copy()

        attrs = []
        for attr in schema["attributes"]:
            new_attr = SchemaAttribute()
            new_attr.kind = attr["class"]
            new_attr.name = attr["name"]
            new_attr.description = attr["description"] if "description" in attr else None
            new_attr.units = attr["units"] if "units" in attr else None
            attrs.append(new_attr)
        del schema["attributes"]
        
        if "extends" in schema:
            parents = schema["extends"]
            del schema["extends"]
        else:
            parents = []
        
        schema_ = Schema()
        dict_to_object(schema, schema_)
        merge_schema_lists(schema_.attributes, attrs)
        
        # Set foreign keys
        if len(parents) > 0:
            attributes = [attr.name for attr in schema_.attributes]
            db_parents = s.query(Schema).filter(Schema.id.in_(parents)).all()
            
            if len(db_parents) != len(parents):
                raise PersistenceError("Could not find all parents")
            # Check parents are of the correct type
            for parent in db_parents:
                if parent.for_ != "schema" and parent.for_ != for_: 
                    raise PersistenceError("Parent %d of different type to ingested schema"%(parent.id))
                for parent_attr in parent.attributes:
                    if parent_attr.name in attributes:
                        raise PersistenceError("Duplicate attribute definition %s from parent %d"%(parent_attr.name, parent.id))
                    attributes.append(parent_attr.name)
                schema_.extends.append(parent)
            
        # Set the schema type
        schema_.for_ = for_

        # If the repo has a method to persist the dataset then call it and record the output
        fn = find_method(self.repo, "persist", "schema")
        if fn != None:
            schema_.repositoryId = fn(schema_)

        return self._persist(schema_, s)
        
    def _persist(self, obj, session):
        """Persists the object using the provided session. Will rollback
        but will not close the session
        """
        try:
            if obj.id == None:
                session.add(obj)
            else:
                session.merge(obj)
            session.flush()
            return obj_to_dict(obj)
        except Exception, e:
            logger.error("Error saving: " + str(e))
            session.rollback()
            raise Exception("Could not save dataset:"+ str(e))
            
    def deleteDataset(self, dataset):
        pass
    
    def getDataset(self, ds_id):
        """Get the dataset as a DTO"""
        s = orm.sessionmaker(bind=self.engine)()
        try:
            return self._getDataset(ds_id, s)
        finally:
            s.close()
        
    def _getDataset(self, ds_id, session):
        """Private method to actually get the dataset using the session provided.
        """
        try:
            obj = session.query(Dataset).filter(Dataset.id == ds_id).one()
            ret = obj_to_dict(obj)
            # Retrieve data_source
            if obj.data_source != None:
                data_source = {}
                data_source["class"] = str(obj.data_source.kind)
                for entry in obj.data_source.parameters:
                    data_source[str(entry.name)] = str(entry.value)
                ret["data_source"] = data_source
            # Retrieve sampling
            if obj.sampling != None:
                sampling = {}
                sampling["class"] = str(obj.sampling.kind)
                for entry in obj.sampling.parameters:
                    sampling[str(entry.name)] = str(entry.value)
                ret["sampling"] = sampling
            return ret
        except NoResultFound, e:
            return None
        
    def enableDataset(self, ds_id):
        """Enable the dataset"""
        session = orm.sessionmaker(bind=self.engine)()
        try:
            obj = session.query(Dataset).filter(Dataset.id == ds_id).one()
            obj.enabled = True
            session.merge(obj)
            session.commit()
        finally:
            session.close()
    
    def disableDataset(self, ds_id):
        """Disable the dataset"""
        session = orm.sessionmaker(bind=self.engine)()
        try:
            obj = session.query(Dataset).filter(Dataset.id == ds_id).one()
            obj.enabled = False
            session.merge(obj)
            session.commit()
        finally:
            session.close()
        
    def getActiveDatasets(self):
        """Returns all enabled datasets."""
        s = orm.sessionmaker(bind=self.engine)()
        try:
            objs = s.query(Dataset).filter(Dataset.enabled == True).all()
            ret_list = []
            for obj in objs:
                ret = obj_to_dict(obj)
                # Retrieve data_source
                if obj.data_source != None:
                    data_source = {}
                    data_source["class"] = str(obj.data_source.kind)
                    for entry in obj.data_source.parameters:
                        data_source[str(entry.name)] = str(entry.value)
                    ret["data_source"] = data_source
                # Retrieve sampling
                if obj.sampling != None:
                    sampling = {}
                    sampling["class"] = str(obj.sampling.kind)
                    for entry in obj.sampling.parameters:
                        sampling[str(entry.name)] = str(entry.value)
                    ret["sampling"] = sampling
                ret_list.append(ret)
            return ret_list
        except NoResultFound, e:
            return []
        finally:
            s.close()
    
    def getSchema(self, s_id):
        """Get the schema as a DTO"""
        session = orm.sessionmaker(bind=self.engine)()
        try:
            obj = session.query(Schema).filter(Schema.id == s_id).one()
            schema = obj_to_dict(obj)
            return schema
        finally:
            session.close()
            
    def getLocation(self, loc_id):
        """Get the location as a DTO"""
        session = orm.sessionmaker(bind=self.engine)()
        try:
            obj = session.query(Location).filter(Location.id == loc_id).one()
            return obj_to_dict(obj)
        finally:
            session.close()

    def logIngesterEvent(self, dataset_id, timestamp, level, message):
        s = orm.sessionmaker(bind=self.engine)()
        try:
            log = IngesterLog()
            log.dataset_id = dataset_id
            log.timestamp = timestamp
            log.level = level
            log.message = message
            s.add(log)
            s.flush()
            s.commit()
        finally:
            s.close()
    
    def getIngesterEvents(self, dataset_id):
        s = orm.sessionmaker(bind=self.engine)()
        try:
            objs = s.query(IngesterLog).filter(IngesterLog.dataset_id == dataset_id).all()
            ret_list = []
            for obj in objs:
                ret_list.append(obj_to_dict(obj))
            return ret_list
        finally:
            s.close()
            
    def persistSamplerState(self, s_id, state):
        self.samplers[s_id] = state
    
    def getSamplerState(self, s_id):
        if id not in self.samplers: return {}
        return self.samplers[s_id]

    def persistDataSourceState(self, ds_id, state):
        self.data_source[ds_id] = state

    def getDataSourceState(self, ds_id):
        if ds_id not in self.data_source: return {}
        return self.data_source[ds_id]

    def findDatasets(self, **kwargs):
        """Find all datasets with the provided attributes"""
        session = orm.sessionmaker(bind=self.engine)()
        try:
            objs = session.query(Dataset).all()
            ret_list = []
            for obj in objs:
                ret_list.append(obj_to_dict(obj))
            return ret_list
        finally:
            session.close()

    def findObservations(self, d_id):
        return self.repo.findObservations(self.getDataset(d_id))

    @method("persist", "data_entry")
    def persistDataEntry(self, data_entry, session, cwd):
        dataset_id = data_entry["dataset"]
        timestamp = parse_timestamp(data_entry["timestamp"])
        dataset = self.getDataset(dataset_id)
        return self.persistObservation(dataset, timestamp, data_entry["data"], None)

    def persistObservation(self, dataset, timestamp, obs, cwd):
        """Persist the observation to the repository. This method is also responsible for 
        notifying the ingester of any new data, such that triggers can be invoked.
        :param dataset: A dataset dict for the target dataset
        :param timestamp: DateTime representation of the timestamp
        :param obs: Dict of attributes to ingest
        :param cwd: Working directory for this ingest
        """
        schema = self.getSchema(dataset["schema"])
        identifier = self.repo.persistObservation(dataset, schema, timestamp, obs, cwd)
        self.ingester.notifyNewObservation(identifier, dataset, obs, cwd)
        return identifier

    def runIngester(self, d_id):
        """Run the ingester for the given dataset ID"""
        self.ingester.queue(self.getDataset(d_id))

