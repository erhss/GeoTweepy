'''

    GeoTwPy.py
    By: Sam Siu, Shreejan Paudel, Damon Li, Allen Yu
    Last Updated: April 17th, 2017

    This application uses tweepy to query for tweets, geocoder to handle API calls to a variety of free Geo-coding
    services (ArcGIS is used by default), and Tkinter to create the GUI.

    Tweets with a valid, non-empty user location are geo-coded (geo-coded locations at the national/country level are discarded), and saved
    as either CSV and/or GeoJSON (dependent on user instructions).

'''
# System libraries
import sys, csv, codecs, datetime, json, threading, os, time

# Twitter library
import tweepy

# Geocoding libraries
import geocoder, pycountry
from geojson import Point

# File dialog libraries
import tkinter as tk
from tkinter import *
import tkinter.messagebox as tkMessageBox
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import asksaveasfilename

# The enums-but-not-really-enums declarations. C-style but without any of the type safety, aka glorified global variarables. 
# Service type enums
ENUM_SERVICE_MAPQUEST = 0
ENUM_SERVICE_NOMINATIM = 1
ENUM_SERVICE_ARCGIS = 2
MAPQUEST_KEY = '<key>'

# Status enums
ENUM_STATUS_OK = 0
ENUM_STATUS_API_429 = 1
ENUM_STATUS_BAD_API = 2
ENUM_STATUS_BAD_WRITE_CSV = 3
ENUM_STATUS_BAD_WRITE_JSON = 4
# Allow non-bmp (e.g. arabic, whatever) characters to be displayed/printed.
#non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd)

CSV_FILESAVEOPTIONS = dict()
CSV_FILESAVEOPTIONS['defaultextension'] = '.csv'
CSV_FILESAVEOPTIONS['filetypes'] = [('Comma Delimited Values files', '.csv')]
CSV_FILESAVEOPTIONS['initialfile'] = 'SaveFile.csv'

JSON_FILEOPENOPTIONS = dict()
JSON_FILEOPENOPTIONS['defaultextension'] = '.json'
JSON_FILEOPENOPTIONS['filetypes'] = [('JavaScript Object Notation (JSON) files', '.json')]

GEOJSON_FILEOPENOPTIONS = dict()
GEOJSON_FILEOPENOPTIONS['defaultextension'] = '.geojson'
GEOJSON_FILEOPENOPTIONS['filetypes'] = [('GeoJSON files', '.geojson')]
GEOJSON_FILEOPENOPTIONS['initialfile'] = 'SaveFile.geojson'


class App(object):
    def __init__(self):
        self.root = Tk()
        self.root.geometry("950x550")
        self.root.wm_title("Query selection")
        self.root.configure(background="gray75")
        # Input query instructions
        self.inputLabel = Text(self.root, height=1.1, borderwidth=0.5, width = 125, background="yellow")

        #hyperlink = Tk.tkHyperlinkManager.HyperlinkManager(self.inputLabel)        
        self.inputLabel.insert(1.0, "Input your query, following the formatting of the Twitter API at https://dev.twitter.com/rest/public/search")
        #self.inputLabel.insert("Twitter API", hyperlink.add(clickHyper))
        self.inputLabel.pack()
        self.inputLabel.configure(state="disabled")

        # Entry box for the query
        self.queryentrytext = StringVar()
        Entry(self.root, textvariable = self.queryentrytext, width = 300).pack(pady = (0,10))

        # Label for the since date
        self.label = Text(self.root, height=1.1, borderwidth=0.5, width = 70, background="yellow")
        self.label.insert(1.0,"Search tweets since the date (in the format YYYY-MM-DD) [OPTIONAL]")
        self.label.pack()
        self.label.configure(state="disabled")

        # Entry box for the since date
        self.sinceentrytext = StringVar()
        Entry(self.root, textvariable = self.sinceentrytext, width = 50).pack(pady = (0,10))

        # Label for the until date
        self.label = Text(self.root, height=1.1, borderwidth=0.5, width = 70, background="yellow")
        self.label.insert(1.0,"Search tweets before the date (in the format YYYY-MM-DD) [OPTIONAL]")
        self.label.pack()
        self.label.configure(state="disabled")

        # Entry box for the until date
        self.untilentrytext = StringVar()
        Entry(self.root, textvariable = self.untilentrytext, width = 50).pack(pady = (0,10))

        # CSV file save path, label and entry box
        self.label = Text(self.root, height=1.1, borderwidth=0.5, width = 50, background="yellow")
        self.label.insert(1.0,"Save CSV results in the file:")
        self.label.pack()
        self.label.configure(state="disabled")

        self.csvpathentrytext = StringVar()
        self.csvEntry = Entry(self.root, textvariable = self.csvpathentrytext, width = 67)
        self.csvEntry.pack()

        self.csvbuttontext = StringVar()
        self.csvbuttontext.set("Browse ... ")
        self.csvbutton = Button(self.root, textvariable=self.csvbuttontext, command=self.browseCSVClicked)
        self.csvbutton.pack(pady = (0,10))       

        # geoJSON file save path
        self.label = Text(self.root, height=1.1, borderwidth=0.5, width = 50, background="yellow")
        self.label.insert(1.0,"Save GeoJSON results in the file:")
        self.label.pack()
        self.label.configure(state="disabled")

        self.jsonpathentrytext = StringVar()
        self.jsonEntry = Entry(self.root, textvariable = self.jsonpathentrytext, width = 67)
        self.jsonEntry.pack()

        self.jsonbuttontext = StringVar()
        self.jsonbuttontext.set("Browse ... ")
        self.jsonbutton = Button(self.root, textvariable=self.jsonbuttontext, command=self.browseJSONClicked)
        self.jsonbutton.pack(pady = (0,10))

        # Twitter Authentication   
        self.label = Text(self.root, height=1.1, borderwidth=0.5, width = 65, background="yellow")
        self.label.insert(1.0,"Select the Twitter API key json file (see README for details)")
        self.label.pack()
        self.label.configure(state="disabled")

        self.apipathentrytext = StringVar()
        self.apiEntry = Entry(self.root, textvariable = self.apipathentrytext, width = 67)
        self.apiEntry.pack()

        self.apibuttontext = StringVar()
        self.apibuttontext.set("Browse ... ")
        self.apibutton = Button(self.root, textvariable=self.apibuttontext, command=self.browseAPIClicked)
        self.apibutton.pack(pady = (0,10))

        # Spinbox for max tweets to search        
        self.label = Text(self.root, height=1.1, borderwidth=0.5, width = 50, background="yellow")
        self.label.insert(1.0,"Specify the maximum number of tweets to search.")
        self.label.pack()
        self.label.configure(state="disabled")

        self.spinboxtext = StringVar()
        self.spinboxtext.set("100")
        self.spinbox = Spinbox(self.root, from_=1, to=2000, textvariable = self.spinboxtext)
        self.spinbox.pack()
        
        
        # The "go" button
        self.gobuttontext = StringVar()
        self.gobuttontext.set("Go!")
        self.gobutton = Button(self.root, textvariable=self.gobuttontext, command=self.goClicked)
        self.gobutton.pack(pady = 10)

        # Label at the bottom, contains useful information for user (e.g. status updates etc)
        self.endLabel = Label (self.root, text="", background="gray75")
        self.endLabel.pack(pady = 10)
        self.root.mainloop()

    def clickHyper(self):
        print ("hyper clicked")

    def browseCSVClicked(self):
        path = getSaveName("CSV file", CSV_FILESAVEOPTIONS)
        if path and not path.endswith(".csv"):
            path += ".csv"
        self.csvpathentrytext.set(path)
        
    def browseJSONClicked(self):
        path = getSaveName("GeoJson file", GEOJSON_FILEOPENOPTIONS)
        if path and not path.endswith(".geojson"):
            path += ".geojson"
        self.jsonpathentrytext.set(path)
        
    def browseAPIClicked(self):
        path = askopenfilename(title='Select the JSON file containing your Twitter API credentials', **JSON_FILEOPENOPTIONS)
        if not os.path.exists(path):
            tkMessageBox.showerror ("Invalid file", "File does not exist")
            return
        self.apipathentrytext.set(path)
    
    def goClicked(self):
        
        search = self.queryentrytext.get()
        since = self.sinceentrytext.get()
        until = self.untilentrytext.get()
        csvPath = self.csvpathentrytext.get()
        jsonPath = self.jsonpathentrytext.get()
        apiPath = self.apipathentrytext.get()

        
        if not search:
            tkMessageBox.showerror ("Invalid query", "Please enter a query.")
            return
        if not apiPath or not os.path.exists(apiPath):
            tkMessageBox.showerror ("Invalid file path", "API key file path does not exist")
            return
        if not csvPath and not jsonPath:
            tkMessageBox.showerror ("No path specified", "Please specify a save path to either a CSV file or geoJSON file")
            return
        if csvPath and not os.path.exists(os.path.dirname(csvPath)):
            tkMessageBox.showerror ("Invalid path", "The target save directory of the CSV file does not exist!")
            return
        if jsonPath and not os.path.exists(os.path.dirname(jsonPath)):
            tkMessageBox.showerror ("Invalid path", "The target save directory of the geoJSON file does not exist!")
            return

        try:
            iNumSearches = int(self.spinboxtext.get())
        except ValueError:
            tkMessageBox.showerror ("Invalid number", "Maximum number of searches must be numeric.")
            return           
        
        showText = "Now querying for: '"+search+"'"
        self.endLabel.configure(text=showText)
        self.endLabel.configure(background="white")
        self.gobuttontext.set("Processing...")
        self.gobutton.configure(state='disabled')
        t1 = threading.Thread(target = self.run, args = (search, since, until, csvPath, jsonPath, apiPath, iNumSearches))
        t1.start()

    def button_click(self, e):
        pass

    # Run the program (on a second thread!)
    def run(self, search, since, until, csvPath, jsonPath, apiFilePath, iNumSearches):        
        status = self.process(search, since, until, csvPath, jsonPath, apiFilePath, iNumSearches)
        if status == ENUM_STATUS_OK:
            tkMessageBox.showinfo ("Finished", "Processing of query has been sucessfully completed.")
        elif status == ENUM_STATUS_API_429:
            tkMessageBox.showwarning ("Finished", "Processing of query has been completed, but the API key has hit its rate limit.\n Please wait 15 minutes before trying again.")
        elif status == ENUM_STATUS_BAD_API:
            tkMessageBox.showerror("API connection error", "Could not connect to Twitter API. Please check your internet connection & your API secret key & token")
        self.gobutton.configure(state='normal')
        self.gobuttontext.set("Go!")
        self.endLabel.configure(text="")
        self.endLabel.configure(background="gray75")


    # Function to query and geocode the tweets
    def process(self, strSearch, strSince, strUntil, csvName, geojsonName, apiFilePath, iNumSearches):
        # Define gecode service to use
        geocodeService = ENUM_SERVICE_ARCGIS
        rtnValue = ENUM_STATUS_OK
        #sys.stdout = codecs.getwriter('utf8')(sys.stdout) # in case this is needed again..
        
        # Initialize header & indices (for CSV writing)
        header = ['Latitude', 'Longitude', 'Location', 'TimeZone', 'Num Retweets', 'Favorited', 'Date', "Coords", "Geo", "Text", "Search"]
        indexLat = header.index("Latitude")
        indexLon = header.index("Longitude")
        indexLoc = header.index("Location")
        indexTimeZone = header.index("TimeZone")
        indexRetweets = header.index("Num Retweets")
        indexFav = header.index("Favorited")
        indexDate = header.index("Date")
        indexCoords = header.index("Coords")
        indexGeo = header.index("Geo")
        indexText = header.index("Text")
        indexSearch = header.index("Search")    
        entries = list()

        # Geojson setup
        geojson = dict()
        geojson["type"] = "FeatureCollection"
        features = list()
        
        # Get the API object
        api = getTwitterAPI(apiFilePath)
        total = 0
        latlon = 0
        geocode = 0
        if api is None:
            rtnValue = ENUM_STATUS_BAD_API
            return rtnValue
        try:
            
            for tweet in tweepy.Cursor(api.search, q=strSearch, since=strSince, until=strUntil, lang="en").items(iNumSearches):

                total += 1

                entry = ["None" for i in range(len(header))]
                # initialize the entry
                entry[indexLoc] = str(tweet.author.location)
                entry[indexTimeZone] = str(tweet.author.time_zone)
                entry[indexText] = str(tweet.text).encode('utf-8').strip()
                entry[indexRetweets] = str(tweet.retweet_count)
                entry[indexFav] = str(tweet.favorited)
                entry[indexDate] = (tweet.created_at).strftime('%m/%d/%Y')
                entry[indexCoords] = str(tweet.coordinates)
                entry[indexGeo] = str(tweet.geo)
                entry[indexSearch] = strSearch
                strLat = "None"
                strLon = "None"

                bGeo = False
                
                # If the tweet is already geocoded
                total += 1
                if entry[indexGeo] != "None":
                    geo = eval(entry[indexGeo])
                    entry[indexLat] = geo['coordinates'][0]
                    entry[indexLon] = geo['coordinates'][1]
                    bGeo = True
                    latlon += 1
                # Otherwise geolocate it if a location is available
                else:
                    if entry[indexLoc] != "None" and entry[indexLoc] != "":
                        latLon = self.GeoCodeLocation(entry[indexLoc], geocodeService)
                        if latLon is not None:
                            entry[indexLat] = latLon[0]
                            entry[indexLon] = latLon[1]
                            bGeo = True
                            geocode += 1
                
                if bGeo:
                    entries.append(entry)                
                    feature = dict()
                    feature["type"] = "Feature"
                    jsonEntry = dict()
                    for index, element in enumerate(header):
                        if element == "Text":
                            jsonEntry[element] = entry[index].decode('utf-8')
                        else:
                            jsonEntry[element] = entry[index]
                    feature["properties"] = jsonEntry     
                    feature["geometry"] = (Point((entry[indexLon], entry[indexLat])))
            
                    features.append(feature)
        # Twitter threw us an error. 
        except tweepy.error.TweepError:
            print ("Rate limit exceeded. Please try again in 15 minutes.")
            print ("Total: "+str(total)+" LatLon: "+str(latlon)+" Geocode: "+str(geocode))
            rtnValue = ENUM_STATUS_API_429

        print ("Total: "+str(total)+" LatLon: "+str(latlon)+" Geocode: "+str(geocode))
        
        geojson["features"] = features
        # If we're writing to csv file
        if (len(entries) > 0):
            if csvName:
                try:
                    with open(csvName, 'w', newline='') as csvfile:
                        spamwriter = csv.writer(csvfile)
                        spamwriter.writerow(header)
                        for row in entries:
                            try:
                                spamwriter.writerow(row)
                            except:
                                print ("Failed to write a csv record")
                except:
                    print ("Failed to open the designated csv save-file")

            # If we're writing to a geojson file
            if geojsonName:
                varName = os.path.basename(geojsonName).replace(".geojson", "").replace(" ", "")
                try:
                    with codecs.open(geojsonName, 'w', encoding='utf-8') as jsonFile:
                        try:
                            json.dump(geojson, jsonFile, ensure_ascii=False)
                        except:
                            print ("Failed to write elements/contents into the specified GeoJSON save-file")
                except:
                    print ("Failed to open the designated GeoJSON save-file")
        
        return rtnValue

    # returns a tuple of (lat, lon)
    def GeoCodeLocation(self, strLocation, service):
        if (service == ENUM_SERVICE_ARCGIS):
            # Get the geocoded result, and sleep for 1s so we don't overload the rate limit.
            g = geocoder.arcgis(strLocation)
            time.sleep(1.1)
            if ('lat' in g.json and 'lng' in g.json):
                try:
                    pycountry.countries.lookup(g.json['address'])
                    print ("Geocoded result at the country level found; aborting. Query: "+strLocation)
                    return None
                except LookupError:                
                    return (g.json['lat'], g.json['lng'])
            else:            
                print("Attempted to geocode the bogus / unknown location of: "+strLocation)
                return None
            
        elif (service == ENUM_SERVICE_MAPQUEST):
            # Create a new account (for a new API key) using dummy emails as necessary (15,000 requests / month / key, when using a "free" key).
            g = geocoder.mapquest(strLocation, key=MAPQUEST_KEY)
            time.sleep(1)
            if (g.json['quality'] != 'COUNTRY'):     
                return (g.json['lat'], g.json['lng'])
            else:
                print("Geocode returned result at country level for the (bogus?) location: "+strLocation)
                return None            
        
        elif(service == ENUM_SERVICE_NOMINATIM):
            geolocator = Nominatim()
            location = geolocator.geocode(strLocation)
            time.sleep(2)
            if location is not None:
                return (location.latitude, location.longitude)
            else:
                return None
        else:
            print("Invalid service specified for GeoCodeLocation")
            return None

# Function to get the twitter API object
def getTwitterAPI(apiFilePath):
    try:    
        # Tweepy keys and tokens (note: keep these secured somewhere safe)
        with open(apiFilePath) as data_file:    
            data = json.load(data_file)
        
        strConsumerKey = data["ConsumerKey"]
        strConsumerSecret = data["ConsumerSecret"]
        strAccessToken = data["AccessToken"]
        strAccessTokenSecret = data["AccessTokenSecret"]

        # Authentication
        auth = tweepy.OAuthHandler(strConsumerKey, strConsumerSecret)
        auth.set_access_token(strAccessToken, strAccessTokenSecret)
        api = tweepy.API(auth)
        return api
    except:
        return None

# Wrapper function for a file-dialog to get a save-file path,
def getSaveName(fileType = "", fileOptions = {}):
    titleText = 'Please specify the file name for your '+fileType
    if fileOptions is not False:
        path = asksaveasfilename(title=titleText, **fileOptions)
    else:
        path = asksaveasfilename(title=titleText)
        
    if not path:
        tkMessageBox.showerror("No file name detected", "Please enter a name for your "+fileType)
    return path



App()
