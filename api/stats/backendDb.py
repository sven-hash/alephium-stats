import datetime

import psycopg2

from utils import DB_BACKEND_HOST,DB_BACKEND_PASSWORD,DB_BACKEND_USER


class BackendDB:

    def __init__(self):
        try:
            self.conn = psycopg2.connect(database="explorer",
                                    host=DB_BACKEND_HOST,
                                    user=DB_BACKEND_USER,
                                    password=DB_BACKEND_PASSWORD,
                                    port="5432")
            self.cur = self.conn.cursor()
        except:
            print("Database not connected successfully")

    def getMinedAlph(self):
        pass

    def getBurnedAlph(self, timeFrom):
        now = datetime.datetime.utcnow()

        query = f"select sum((gas_amount*gas_price)/10^18)/2 from transactions where main_chain = true"\
                f" and block_timestamp BETWEEN {timeFrom} and {now.timestamp()*1000}"


        self.cur.execute(query)
        rec = self.cur.fetchone()
        self.conn.close()

        return rec[0]
