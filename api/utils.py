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
    def getCountry(ip,s,token):

        try:
            url = f'https://ipinfo.io/{ip}?token={token}'
            response = s.get(url)

            if response.ok:
                data = response.json()
                return {'country': data['country'], 'city': data['city'], 'region': data['region'], 'org': data['org']}
            else:
                print(response.json())
                return {}

            '''
            IP = data['ip']
            org = data['org']
            city = data['city']
            region = data['region']
            '''

        except requests.RequestException as e:
            print(e)
            return {}
