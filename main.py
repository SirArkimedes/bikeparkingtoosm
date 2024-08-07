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


class Point:
  lat: float
  lon: float
  type: ParkingType
  capacity: int | None

  def __init__(self, lat: float, lon: float, type: ParkingType, capacity: int | None):
    self.lat = lat
    self.lon = lon
    self.type = type
    self.capacity = capacity

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

  create_osm_change_from(points)
  print("DONE")

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
  api = auth_osm()

  with api.Changeset({"comment": "Just repair stations"}) as changeset_id:
    print(f"Part of Changeset {changeset_id}")
    for i, point in enumerate(points):
      print(f"Processing repair station ({i+1} / {len(points)}): ", point)
      if point.type == ParkingType.REPAIR_STATION:
        print("Creating repair station")
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

def read_csv() -> list[Point]:
  all_points = []
  with open('data/points.csv', newline='\n') as file:
    reader = csv.reader(file, delimiter=' ', quotechar='|')

    last_point = None
    for row in reader:
        if len(row) > 0 and row[0] == '\"POINT':
          lon_row = row[1]
          lat_row = row[2]
          lat = lat_row.split(')')[0]
          lon = lon_row.split('(')[1]
          type_string = lat_row.split(',')[1]

          # Rows that have a space in their type (e.g. "Inverted U") have an extra array element.
          # So we need to append the first part of that next element to the type string.
          if len(row) > 4:
            type_string += " " + row[3].split(',')[0]
          # Special case for a Bike Locker one.
          elif len(row) == 4 and (type_string == "Inverted" or type_string == "Bike"):
            new_type = type_string + " " + row[3].split(',')[0]
            if type_string_to_enum(new_type) != ParkingType.UNKNOWN:
              type_string = new_type

          type = type_string_to_enum(type_string)

          capacity: int | None = None
          if len(row) == 3:
            capacity_split = lat_row.split(",")
            if len(capacity_split) > 2 and capacity_split[2].__contains__("Capacity:"):
              capacity = int(capacity_split[2].replace("Capacity:", ""))
          elif len(row) == 4:
            capacity_row = row[3].split(',')
            if len(capacity_row) > 1:
              if capacity_row[1].__contains__("Capacity:"):
                capacity = int(capacity_row[1].replace("Capacity:", ""))
              else:
                capacity = int(capacity_row[1])
            elif capacity_row[0].isnumeric():
              capacity = int(capacity_row[0])
          elif len(row) == 5 and type != ParkingType.REPAIR_STATION:
            capacity = int(row[4])

          last_point = Point(
            float(lat),
            float(lon),
            type,
            capacity,
          )
          all_points.append(last_point)

          if capacity is None:
            # Capacity isn't on this row, we need to move to the next row to capture it.
            pass
        elif last_point is not None and last_point.capacity is None and last_point.type != ParkingType.REPAIR_STATION:
          last_point.capacity = int(row[1].split(',')[0])

    return all_points

def main() -> int:
  setup()
  return 0

if __name__ == '__main__':
  sys.exit(main())
