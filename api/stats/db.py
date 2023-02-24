import logging
from datetime import datetime

from peewee import *
from playhouse.flask_utils import PaginatedQuery

database = SqliteDatabase('./data.db', pragmas={'foreign_keys': 1})

logger = logging.getLogger('db')
logHandler = logging.getLogger('db')
logHandler.setLevel(logging.DEBUG)


class BaseModel(Model):
    def connect(self):
        logging.getLogger('address')

        try:
            database.connect()
        except Exception as e:
            logHandler.exception(e)

    def close(self):
        logHandler = logging.getLogger('address')

        try:
            database.close()
        except Exception as e:
            logHandler.exception(e)

    def insertGenesis(self, address, balance):
        self.connect()

        try:
            with database.atomic():
                addrId = Address.get(Address.address == address)
                addr = Genesis.get_or_none(addressFK=addrId)

                if addr is None:
                    Genesis.create(addressFK=addrId, balanceGenesis=balance)

        except IntegrityError as e:
            logHandler.exception(e)
            return False
        except DoesNotExist as e:
            logHandler.exception(e)
            return False
        finally:
            self.close()

    def insertAddress(self, address, balance=0, locked=0):
        logHandler = logging.getLogger('address')
        logHandler.debug(address)
        self.connect()

        try:
            with database.atomic():

                addr = Address.get_or_none(address=address)
                if addr is None:
                    Address.create(address=address, balance=balance, locked=locked)

        except IntegrityError as e:
            logHandler.exception(e)
            return False
        except DoesNotExist as e:
            logHandler.exception(e)
            return False
        finally:
            self.close()

    def insertManyAddress(self, addresses):
        rows = list()

        for addr in addresses:
            rows.append({'address': addr})

        try:
            with database.atomic():
                for batch in chunked(rows, 5000):
                    Address.insert_many(batch).on_conflict_ignore().execute()

        finally:
            self.close()

    def insertTxHistory(self, txsHistory):
        try:
            with database.atomic():
                for data in txsHistory:

                    addrId = Address.get(Address.address == data['address'])

                    cleanData = {}
                    for k,v in data.items():
                        if v is not None:
                            cleanData[k]= v


                    txAddrId, created = TxHistory.get_or_create(addressFK=addrId,
                                                              defaults=cleanData)
                    if not(created):
                        del cleanData['address']
                        TxHistory.update(**cleanData) \
                            .where(TxHistory.id == txAddrId).execute()

        finally:
            self.close()

    def insertManyPeer(self, peers):
        rows = list()

        try:
            with database.atomic():
                for peer, data in peers.items():
                    ipInfo = data[0]

                    now = datetime.now()

                    # not the best way, this is ugly
                    Peer.insert(
                        ip=peer, client_version=data[1]['version'], isSynced=data[2]['isSynced'],
                        unreachable=data[3]['unreachable'],
                        country=ipInfo['country'],
                        region=ipInfo['region'], city=ipInfo['city'], org=ipInfo['org'],
                        updated_on=now, created_on=now
                    ).on_conflict(action="update", conflict_target=[Peer.ip],
                                  update={'ip': peer, 'client_version': data[1]['version'],
                                          'isSynced': data[2]['isSynced'],
                                          'unreachable': data[3]['unreachable'],
                                          'country': ipInfo['country'],
                                          'region': ipInfo['region'], 'city': ipInfo['city'], 'org': ipInfo['org'],
                                          'updated_on': datetime.now()}).execute()


        finally:
            self.close()

    def updateBalance(self, addresses):
        logHandler = logging.getLogger('address')
        logHandler.debug(addresses)
        self.connect()

        try:
            with database.atomic():
                for addr in addresses:
                    Address.update(addr).where(addr['address'] == Address.address).execute()
        except IntegrityError as e:
            logHandler.exception(e)
            return False
        except DoesNotExist as e:
            logHandler.exception(e)
            return False
        finally:
            self.close()

    def getTxAddressWithFirst(self):
        self.connect()

        data = list(TxHistory.select().where((TxHistory.first_tx_recv) & (TxHistory.first_tx_send)). \
                    join(Address).dicts())

        self.close()
        return data

    def getTxAddressWithoutFirst(self):
        self.connect()

        data = list(TxHistory.select(Address.address,TxHistory).where((TxHistory.first_tx_recv.is_null()) | (TxHistory.first_tx_send.is_null())). \
                    join(Address).dicts())

        self.close()
        return data

    def getTxAddress(self,page,size=10,address=None):
        self.connect()

        if address is not None:

            addrId = Address.get(Address.address == address)
            data = list(TxHistory.select(Address.address, TxHistory.first_tx_recv,
                                         TxHistory.first_tx_send, TxHistory.last_tx_recv, TxHistory.last_tx_send,
                                         TxHistory.created_on, TxHistory.updated_on).where(TxHistory.addressFK == addrId).
                        join(Address).dicts())

        elif page is not None:
            data = list(TxHistory.select(Address.address, TxHistory.first_tx_recv,
                                         TxHistory.first_tx_send, TxHistory.last_tx_recv, TxHistory.last_tx_send,
                                         TxHistory.created_on, TxHistory.updated_on). \
                        join(Address).paginate(page, size).dicts())
        else:
            data = list(TxHistory.select(Address.address, TxHistory.first_tx_recv,
                                         TxHistory.first_tx_send, TxHistory.last_tx_recv, TxHistory.last_tx_send,
                                         TxHistory.created_on, TxHistory.updated_on). \
                        join(Address).dicts())

        self.close()
        return data

    def getTxAddressToUpdate(self,date):
        self.connect()
        data = list(TxHistory.select(Address.address).where(
            TxHistory.updated_on <= date).join(Address).dicts())
        self.close()
        return data

    def getPeers(self):
        self.connect()

        data = [peer for peer in
                Peer.select(Peer.client_version, Peer.created_on, Peer.updated_on, Peer.country, Peer.region, Peer.city,
                            Peer.org, Peer.isSynced, Peer.unreachable).dicts()]

        self.close()
        return data

    def getNames(self):
        self.connect()

        data = [name for name in
                Name.select(Name.name, Name.exchangeName, Name.state, Name.type, Address.address).join(Address).dicts()]

        self.close()
        return data

    def getGenesis(self):
        self.connect()

        data = [address for address in
                Genesis.select(Address.address, Genesis.balanceGenesis, Address.balance, Address.locked).join(
                    Address).order_by(Genesis.balanceGenesis.desc()).dicts()]
        self.close()
        return data

    def getOrderedBalanceAddresses(self, limit, page, size):
        self.connect()
        if limit > 0:
            data = [address for address in Address.select(Address.address, Address.updated_on, Address.balance,
                                                          Address.locked, Name.name, Name.state, Name.exchangeName,
                                                          Name.type,Address.id,TxHistory.first_tx_send,TxHistory.first_tx_recv,
                                                          TxHistory.last_tx_send,TxHistory.last_tx_recv).
            join(Name, join_type=JOIN.LEFT_OUTER).switch(Address).join(TxHistory).limit(limit)
            .order_by(Address.balance.desc()).dicts()]
            print(data)

        elif page is not None:

            data = list(Address.select(Address.address, Address.updated_on, Address.balance,
                                                          Address.locked, Name.name, Name.state, Name.exchangeName,
                                                          Name.type,Address.id,TxHistory.first_tx_send,TxHistory.first_tx_recv,
                                                          TxHistory.last_tx_send,TxHistory.last_tx_recv).
            join(Name, join_type=JOIN.LEFT_OUTER).switch(Address).join(TxHistory).
                paginate(page, size).dicts())

        else:
            data = [address for address in Address.select(Address.address, Address.updated_on, Address.balance,
                                                          Address.locked, Name.name, Name.state, Name.exchangeName,
                                                          Name.type,Address.id,TxHistory.first_tx_send,TxHistory.first_tx_recv,
                                                          TxHistory.last_tx_send,TxHistory.last_tx_recv).
            join(Name, join_type=JOIN.LEFT_OUTER).switch(Address).join(TxHistory).dicts()]

        self.close()

        return data

    def getAddressByDate(self, date):
        self.connect()
        data = [address for address in Address.select(Address.address, Address.created_on, Address.id).where(
            Address.updated_on <= date).dicts()]
        self.close()
        return data

    def getAllAddresses(self):
        self.connect()
        data = [address for address in Address.select().dicts()]
        self.close()
        return data

    def getTimeLastInsert(self):
        try:
            self.connect()
            cursor = \
                [data for data in
                 database.execute_sql('select created_on from address order by created_on desc LIMIT 1')][
                    0][0]
            self.close()
            return int(datetime.timestamp(datetime.strptime(cursor, '%Y-%m-%d %H:%M:%S.%f')))
        except Exception as e:
            print(e)
            return None

    def countAddresses(self):
        try:
            self.connect()
            count = Address.select().count()

            self.close()

            return count
        except Exception as e:
            print(e)
            return None

    def getTotalLocked(self):
        try:
            self.connect()
            totalLocked = [i for i in database.execute_sql('select sum(locked) from address')][0][0]

            self.close()

            return totalLocked
        except Exception as e:
            print(e)
            return None

    def getTotalBalance(self):
        try:
            self.connect()
            totalBalance = [i for i in database.execute_sql('select sum(balance) from address')][0][0]

            self.close()

            return totalBalance
        except Exception as e:
            print(e)
            return None

    def getTimeLastUpdateGenesis(self):
        try:
            self.connect()
            cursor = \
                [data for data in
                 database.execute_sql('select updated_on from genesis order by updated_on desc LIMIT 1')][
                    0][0]
            self.close()
            return int(datetime.timestamp(datetime.strptime(cursor, '%Y-%m-%d %H:%M:%S.%f')))
        except Exception as e:
            print(e)
            return None

    def insertName(self, address, name=None, exchangeName=None, state=None, type=None):
        self.connect()

        try:
            with database.atomic():
                addrId = Address.get(Address.address == address)
                addr = Name.get_or_none(addressFK=addrId)

                if addr is None:
                    pass
                    Name.create(addressFK=addrId, name=name, exchangeName=exchangeName, state=state, type=type)

        except IntegrityError as e:
            logHandler.exception(e)
            return False
        except DoesNotExist as e:
            logHandler.exception(e)
            return False
        finally:
            self.close()


class Address(BaseModel):
    class Meta:
        database = database
        db_table = 'address'

    address = TextField(unique=True)
    balance = FloatField(default=0)
    locked = FloatField(default=0)

    created_on = DateTimeField(default=datetime.now)
    updated_on = DateTimeField(default=datetime.now)


class Name(BaseModel):
    class Meta:
        database = database
        db_table = 'name'

    addressFK = ForeignKeyField(Address, backref='name', unique=True)
    name = TextField(null=True)
    exchangeName = TextField(null=True)
    state = TextField(null=True)
    type = TextField(null=True)

    created_on = DateTimeField(default=datetime.now)
    updated_on = DateTimeField(default=datetime.now)


class Genesis(BaseModel):
    class Meta:
        database = database
        db_table = 'genesis'

    addressFK = ForeignKeyField(Address, backref='genesis', null=True)
    balanceGenesis = FloatField(default=0)

    created_on = DateTimeField(default=datetime.now)
    updated_on = DateTimeField(default=datetime.now)


class TxHistory(BaseModel):
    class Meta:
        database = database
        db_table = 'tx_history'

    addressFK = ForeignKeyField(Address, backref='tx_history', unique=True)
    first_tx_recv = TimestampField(default=None, null=True)
    first_tx_send = TimestampField(default=None, null=True)
    last_tx_recv = TimestampField(default=None, null=True)
    last_tx_send = TimestampField(default=None, null=True)

    created_on = DateTimeField(default=datetime.utcnow)
    updated_on = DateTimeField(default=datetime.utcnow)


class Peer(BaseModel):
    class Meta:
        database = database
        db_table = 'peer'

    ip = CharField(unique=True)
    client_version = CharField(null=True)
    country = CharField(null=True)
    region = CharField(null=True)
    city = CharField(null=True)
    org = CharField(null=True)
    isSynced = BooleanField()
    unreachable = BooleanField()

    created_on = DateTimeField(default=datetime.now)
    updated_on = DateTimeField(default=datetime.now)


def create_tables():
    with database:
        database.create_tables([Address, Genesis, Peer, Name, TxHistory])
