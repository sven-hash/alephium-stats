import time

import requests


class Utils:

    @staticmethod
    def humanFormat(num, round_to=2):
        # From https://stackoverflow.com/questions/579310/formatting-long-numbers-as-strings-in-python
        magnitude = 0
        while abs(num) >= 1000:
            magnitude += 1
            num = round(num / 1000.0, round_to)
        return '{:.{}f} {}'.format(num, round_to, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])

    @staticmethod
    def queryIPinfos(ip,s,token=None):

        if token is not None:
            url = f'https://ipinfo.io/{ip}?token={token}'
        else:
            url = f'https://ipapi.co/{ip}/json/'

        response = s.get(url)

        return response


    @staticmethod
    def getCountry(ip,s,token=None):

        try:

            sleepTime = 3
            retries = 1
            response = Utils.queryIPinfos(ip,s, token)

            while not response.ok:
                if retries >= 5:
                    break
                time.sleep(sleepTime)
                sleepTime += 1
                retries += 1

                response = Utils.queryIPinfos(ip,s, token)
                print(f"Throttle sleep {sleepTime}s retries {retries} response {response.json()}")

            if response.ok:
                data = response.json()
                return {'country': data['country'], 'city': data['city'], 'region': data['region'], 'org': data['org']}
            else:
                print(f"Data not inserted error {response.json()}")
                return {}

        except requests.RequestException as e:
            print(e)
            return {}
