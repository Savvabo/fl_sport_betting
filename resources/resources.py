from resources.instagram_parser import InstagramParser
from resources.odds_forecasts import OddsForecasts
from resources.vprognoze_forecasts import VprognozeForecasts
from resources.stavka_forecasts import StavkaForecasts
from resources.vseprosport_forecasts import VseprosportForecasts

RESOURCES = {'instagram': InstagramParser,
             'odds': OddsForecasts,
             'vprognoze': VprognozeForecasts,
             'stavka': StavkaForecasts,
             'vseprosport': VseprosportForecasts}