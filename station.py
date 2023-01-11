from typing import TYPE_CHECKING

import requests
from pyhafas import HafasClient
from pyhafas.profile import DBProfile

client = HafasClient(DBProfile())

if TYPE_CHECKING:
    from direct_destination import DirectDestination


class Station:
    """
    Class for a station.
    """
    name: str
    formal_name: str
    display_name: str
    coordinates: tuple[float]
    identifier: str
    code: str

    def __init__(self, name, formal_name=None, coordinates=None, identifier=None, code=None):
        """
        Initialize a station
        """
        self.name = name # Official station name
        self.formal_name = formal_name # , displayed  in output
        self.coordinates = coordinates
        self.identifier = identifier
        self.code = code
        self.display_name= self.get_display_name()

    def is_in_france(self):
        """
        Check if the station is in France
        :return: True if the station is in France, False otherwise
        """
        # See https://en.wikipedia.org/wiki/List_of_UIC_country_codes
        return self.identifier[:2] == '87'

    # noinspection SpellCheckingInspection
    def name_to_code(self) -> (str, str) or None:
        """
        Get the station code from the station name
        For multiple station in the same city, return generic codes to avoid ambiguity
        (e.g. "Gare de Lyon/ Gare Montparnasse" -> "FRPAR")
        :return: Station code (5 letters)
        """
        # The following mappings prevent error due to outdated stations names in Deutsch Bahn database,
        # for exemple station named 'Saumur Rive Droit' doesn't exist anoymore on SNCFConnect
        # because his name has changed, see 'oldname' on https://www.openstreetmap.org/node/3486337297
        if self.code is not None:
            return self.code, self.name
        elif self.name == 'Aeroport Paris-Charles de Gaulle TGV':
            return 'FRMLW', 'Paris Aéroport Roissy Charles-de-Gaulle'
        elif self.name.startswith('Massy'):
            return 'FRDJU', 'Massy Gare TGV'
        elif self.name.startswith('Le Creusot Montceau'):
            return 'FRMLW', 'Le Creusot - Montceau TGV '
        elif 'Montpellier' in self.name:
            return 'FRMPL', 'Montpellier'
        elif 'Nice' in self.name:
            return 'FRNIC', 'Nice'
        elif self.name == 'Vierzon Ville':
            return 'FRXVZ', 'Vierzon'
        elif self.name == 'Vendôme Villiers sur Loire':
            return 'FRAFM', 'Vendôme'
        elif self.name == 'Moulins-sur-Allier':
            return 'FRXMU', 'Moulins'
        elif self.name == 'Saumur Rive Droit':
            return 'FRACN', 'Saumur'
        elif self.name == 'Orange(Avignon)':
            return 'FRXOG', 'Orange'
        elif self.name.endswith('Ville'):  # endswith because Montauban-Ville-Bourbon
            query = self.name.replace('Ville', '')
        elif self.name.endswith('Hbf'):
            # Hbf == German for central railway station, see https://en.wikipedia.org/wiki/HBF
            query = self.name.replace('Hbf', '')
        else:
            query = self.name
        result = self.get_station_code(query.lower())
        return result

    @staticmethod
    def get_station_code(station_name):
        """
        Get the station code from the station name
        The station code is necessary to request SNCF Connect API
        :param station_name: Station official name
        :return: Station code (5 letters), exemple FRPAR for all Paris Stations
        """

        if station_name == 'paris':
            return 'FRPMO', 'Paris'
        elif station_name == 'lyon':
            return 'FRLPD', 'Lyon'

        cookies = {
            'x-visitor-id': 'fbae435c1650f2c4e99b983ed0a4ab204e7',
            'x-correlationid': '47666724-c4c5-4ef3-8305-2e2b925d5344',
            'x-user-device-id': 'a5e0b96f-e666-4177-b5be-ff990be8439e',
            'x-nav-session-id': '43296fed-d4ea-4214-905d-f8d13c7baadd|1654596298686|1|',
        }

        headers = {
            'accept-language': 'fr-FR,fr;q=0.9',
            'x-bff-key': 'ah1MPO-izehIHD-QZZ9y88n-kku876',
        }


        json_data = {
            'searchTerm': station_name,
            'keepStationsOnly': True,
        }
        station_match = requests.post(
            'https://www.sncf-connect.com/bff/api/v1/autocomplete',
            json=json_data,
            cookies=cookies,
            headers=headers)
        station_match.close()
        if station_match.status_code == 200:
            station_match_json = station_match.json()
            if station_match_json:
                if 'places' in station_match_json:
                    for transport_place in station_match_json['places']['transportPlaces']:
                        if transport_place['type']['label'] == 'Gare':
                            return transport_place['codes'][0]['value'], station_match_json['places']['transportPlaces'][0]['label']
        raise ValueError(f'The station {station_name} does not exist, please use same station name as SNCF connect')

    @classmethod
    def get_farther(cls, departure: 'DirectDestination', arrival: 'DirectDestination',
                    intermediate_station: 'dict') -> 'Station':
        """
        Get the station that is the farthest from the departure station
        :param departure:
        :param arrival:
        :param intermediate_station:
        :return:
        """
        if intermediate_station['station'] in departure.destinations and \
                departure.destinations[intermediate_station['station'].identifier]['duration'] > \
                arrival.destinations[intermediate_station['station'].identifier]['duration']:
            return departure.station
        return intermediate_station['station']

    @classmethod
    def parse(cls, proposal):
        """
        Parse a proposal from the API
        :param proposal: JSON object from the API
        :return: Station object
        """
        return Station(str.lower(proposal['station']['label']),
                       proposal['latitude'],
                       proposal['longitude'],
                       code=proposal['station']['metaData']['PAO']['code'],
                       )

    def get_code(self):
        """
        Get the station code
        :return:
        """
        code, formal_name = Station.get_station_code(self.name.lower())
        self.code = code
        self.formal_name = formal_name

    def get_identifier(self):
        """
        Get the SNCF identifier of the station
        Thanks to Hafas API, get the Deutsch Bahn station identifier from station name
        For exemple Paris --> '8796001'
        This identifier will be used to identify direct destinations thanks to api.direkt.bahn
        """
        if self.identifier is None:
            self.identifier = client.locations(self.name)[0].__dict__['id']

    def get_display_name(self, preserve_official_name=False):
        if preserve_official_name:
            return self.name
        else:
            match self.name:
                case "Montpellier Sud De France":
                    return "Montpellier TGV (SdF)"
                case _:
                    return self.name\
                        .removesuffix(" 1 Et 2")\
                        .removesuffix(' Rhone-Alpes Sud')

PARIS = {
    'station':
        Station(name='Paris', code='FRPLY',
                coordinates=(48.856614, 2.3522219), identifier='8796001')
}
