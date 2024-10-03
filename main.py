from requests_oauth2client import OAuth2Client, OAuth2AuthorizationCodeAuth
import requests
import webbrowser
import csv
import os
import sys


from dotenv import load_dotenv 
import osmapi

class ParkingType: 
  SCHOOL_YARD = "Schoolyard"
  BOLLARD = "Bollard"
  COAT_HANGER = "Coathanger"
  INVERTED_U = "Inverted U"
  WAVE = "Wave"
  BIKE_LOCKER = "Bike Locker"
  HORNED = "Horned"
  SPIRAL = "Spiral"
  WHEEL_WELL = "Wheelwell"
  REPAIR_STATION = "Repair Station"
  VERTICAL = "Vertical"
  SPECIAL = "Special"

  UNKNOWN = "Unknown"

class Obstruction:
  NONE = "None"
  LOW = "Low"
  MEDIUM = "Medium"
  HIGH = "High"
  PAYMENT_REQUIRED = "Payment Required"


class Point:
  lat: float
  lon: float
  type: ParkingType
  capacity: int | None
  obstruction: Obstruction | None
  within_plain_sight: bool | None
  within_view_of_entrance: bool | None

  def __init__(
      self,
      lat: float,
      lon: float,
      type: ParkingType,
      capacity: int | None,
      obstruction: Obstruction | None,
      within_plain_sight: bool | None,
      within_view_of_entrance: bool | None,
    ):
    self.lat = lat
    self.lon = lon
    self.type = type
    self.capacity = capacity
    self.obstruction = obstruction
    self.within_plain_sight = within_plain_sight
    self.within_view_of_entrance = within_view_of_entrance

  def __str__(self):
    return f"Point: lat - {self.lat}, lon - {self.lon}, type - {self.type}, capacity - {self.capacity}"

def auth_osm() -> osmapi.OsmApi:
  client_id = os.getenv("OSM_CLIENT_ID")
  client_secret = os.getenv("OSM_CLIENT_SECRET")
  # special value for redirect_uri for non-web applications
  redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
  authorization_base_url = "https://master.apis.dev.openstreetmap.org/oauth2/authorize"
  token_url = "https://master.apis.dev.openstreetmap.org/oauth2/token"

  oauth2client = OAuth2Client(
      token_endpoint=token_url,
      authorization_endpoint=authorization_base_url,
      redirect_uri=redirect_uri,
      client_id=client_id,
      client_secret=client_secret,
      code_challenge_method=None,
  )

  # open OSM website to authorize user using the write_api and write_notes scope
  scope = ["write_api", "write_notes"]
  az_request = oauth2client.authorization_request(scope=scope)
  print(f"Authorize user using this URL: {az_request.uri}")
  webbrowser.open(az_request.uri)

  # create a new requests session using the OAuth authorization
  auth_code = input("Paste the authorization code here: \n")
  auth = OAuth2AuthorizationCodeAuth(
      oauth2client,
      auth_code,
      redirect_uri=redirect_uri,
  )
  oauth_session = requests.Session()
  oauth_session.auth = auth

  return osmapi.OsmApi(
    api="https://api06.dev.openstreetmap.org",
    session=oauth_session
  )

def setup():
  load_dotenv() 
  
  points = read_csv()
  invalid_points = list(filter(lambda point: point.type == ParkingType.UNKNOWN or (point.capacity is None and point.type != ParkingType.REPAIR_STATION), points))
  if len(invalid_points) > 0:
    print("Invalid points found:")
    for point in invalid_points:
      print(point)
    sys.exit(1)
  else:
    print("No invalid points found. Moving on!")

  print("Total points parsed: ", len(points))

  create_osm_change_from(points)
  print("DONE")

  print("Denver Metro: https://overpass-turbo.eu/s/1S6B")
  print("Lakewood: https://overpass-turbo.eu/s/1LWR")


def data_type_to_osm_type(type: str) -> str:
  # Refer to https://wiki.openstreetmap.org/wiki/Key:bicycle_parking
  if type == ParkingType.SCHOOL_YARD:
    # unclear
    return "rack"
  elif type == ParkingType.BOLLARD:
    return "bollard"
  elif type == ParkingType.COAT_HANGER:
    return "rack"
  elif type == ParkingType.INVERTED_U:
    return "stands"
  elif type == ParkingType.WAVE:
    return "stands"
  elif type == ParkingType.BIKE_LOCKER:
    return "lockers"
  elif type == ParkingType.HORNED:
    # unclear
    return "stands"
  elif type == ParkingType.SPIRAL:
    # unclear
    return "rack"
  elif type == ParkingType.WHEEL_WELL:
    return "wall_loops"
  elif type == ParkingType.REPAIR_STATION:
    return "repair_station"
  elif type == ParkingType.VERTICAL:
    return "upright_stands"
  elif type == ParkingType.SPECIAL:
    # unclear
    return "stands"

def create_osm_change_from(points: list[Point]):
  print("Authorizing OSM API")
  api = auth_osm()

  def exclusion(point: Point) -> bool:
    return (
      # Colorado Mills
      (point.lat == 39.7331874 and point.lon == -105.1558478) #1
      or (point.lat == 39.7310746 and point.lon == -105.158065) #2
      or (point.lat == 39.7364441 and point.lon == -105.1611804) #3

      # Office park North of Colorado Mills
      or (point.lat == 39.7445533 and point.lon == -105.1544491) #4
      or (point.lat == 39.7440516 and point.lon == -105.1557097) #5

      # RTD Federal Center Station
      or (point.lat == 39.719571 and point.lon == -105.1298687) #6
      or (point.lat == 39.7195685 and point.lon == -105.128261) #7

      # RTD Wadsworth Station
      or (point.lat == 39.7366641 and point.lon == -105.0808718) #8
      or (point.lat == 39.7367347 and point.lon == -105.0808295) #9
      or (point.lat == 39.7367715 and point.lon == -105.0807402) #10
      or (point.lat == 39.7366012 and point.lon == -105.0817873) #11

      # Molholm Elementary School
      or (point.lat == 39.7314568 and point.lon == -105.0636275) #12

      # Creighton Middle School
      # 39.7167643 / -105.1062501 -- Go remove this one from OSM. Our data is better.

      # Gold Crown Field House
      or (point.lat == 39.7138648 and point.lon == -105.062346) #13

      # Glennon Heights Elementary School
      # 39.7063184 / -105.1226699 -- Go remove this one from OSM. Our data is better.

      # Lakewood City Commons
      or (point.lat == 39.7081803 and point.lon == -105.0854128) #14
      or (point.lat == 39.7080601 and point.lon == -105.0852599) #15
      or (point.lat == 39.7082932 and point.lon == -105.084945) #16
      or (point.lat == 39.706733 and point.lon == -105.0839718) #17

      # Belmar
      or (point.lat == 39.7080051 and point.lon == -105.0767886) #18

      # Deane Elementary School
      # 39.706048 / -105.0625555, 39.7060477 / -105.0625308 -- Go remove these from OSM. Our data is better.

      # Alameda High School
      or (point.lat == 39.6938518 and point.lon == -105.0850199) #19

      # Carmody Recreation Center
      # 39.6776681 / -105.1092229, 39.677625 / -105.1092238 -- Go remove these from OSM. Our data is better.

      # Bear Creek High School
      or (point.lat == 39.6594614 and point.lon == -105.1100416) #20
      or (point.lat == 39.657092 and point.lon == -105.11043) #21

      # Whole Foods near Littleton
      or (point.lat == 39.6234228 and point.lon == -105.0920043) #22
      # Delete one of the ones on this location. Repair station is not labeled correctly.
    )

  points_without_excluded = list(filter(lambda point: not exclusion(point), points))
  
  print("Creating changeset")
  with api.Changeset({
    "comment": "Add Lakewood Bike Parking",
    "imported_with": "https://github.com/SirArkimedes/bikeparkingtoosm",
    "source": "2024 Lakewood Bike Parking Task Force Collected Data",
    "more_info": "https://www.lakewoodtogether.org/bikeplanupdate",
  }) as changeset_id:
    print(f"Part of Changeset {changeset_id}")
    for i, point in enumerate(points_without_excluded):
      print(f"Processing point ({i+1} / {len(points_without_excluded)}): ", point)
      if point.type == ParkingType.REPAIR_STATION:
        api.NodeCreate(
          {
            "lat": point.lat,
            "lon": point.lon,
            "tag": {
              "amenity": "bicycle_repair_station",
              "service:bicycle:pump": "yes",
              "fee": "no",
            },
          }
        )
      else:
        api.NodeCreate(
          {
            "lat": point.lat,
            "lon": point.lon,
            "tag": {
              "amenity": "bicycle_parking",
              "capacity": f"{point.capacity}",
              "bicycle_parking": data_type_to_osm_type(point.type),
              "fee": "no",
            },
          }
        )


def type_string_to_enum(type_string: str) -> ParkingType:
  if type_string == "Schoolyard":
    return ParkingType.SCHOOL_YARD
  elif type_string == "Bollard":
    return ParkingType.BOLLARD
  elif type_string == "Coathanger":
    return ParkingType.COAT_HANGER
  elif type_string == "Inverted U":
    return ParkingType.INVERTED_U
  elif type_string == "Wave":
    return ParkingType.WAVE
  elif type_string == "Bike Locker":
    return ParkingType.BIKE_LOCKER
  elif type_string == "Horned":
    return ParkingType.HORNED
  elif type_string == "Spiral":
    return ParkingType.SPIRAL
  elif type_string == "Wheelwell":
    return ParkingType.WHEEL_WELL
  elif type_string == "Repair Station":
    return ParkingType.REPAIR_STATION
  elif type_string == "Vertical":
    return ParkingType.VERTICAL
  elif type_string == "Special":
    return ParkingType.SPECIAL
  else:
    return ParkingType.UNKNOWN
  
def obstruction_string_to_enum(obstruction_string: str) -> Obstruction:
  if obstruction_string == "none":
    return Obstruction.NONE
  elif obstruction_string == "low":
    return Obstruction.LOW
  elif obstruction_string == "medium":
    return Obstruction.MEDIUM
  elif obstruction_string == "high":
    return Obstruction.HIGH
  elif obstruction_string == "payment required":
    return Obstruction.PAYMENT_REQUIRED
  else:
    return Obstruction.NONE

def read_csv() -> list[Point]:
  print("Processing CSV")
  all_points = []
  with open('data/points.csv', newline='\n') as file:
    reader = csv.reader(file, delimiter=',', quotechar='|')

    for row in reader:
      lon = float(row[0])
      lat = float(row[1])
      type = type_string_to_enum(row[2])
      if type != ParkingType.REPAIR_STATION:
        capacity = None if row[3] is None else int(row[3])
        obstruction = obstruction_string_to_enum(row[4].lower())
        within_plain_sight = None if row[5] is None else row[5] == "1"
        within_view_of_entrance = None if row[6] is None else row[6] == "1"

      point = Point(lat, lon, type, capacity, obstruction, within_plain_sight, within_view_of_entrance)
      all_points.append(point)

    return all_points

def main() -> int:
  setup()
  return 0

if __name__ == '__main__':
  sys.exit(main())
