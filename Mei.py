import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime   
from datetime import date

def main():
    # Series to check and download
    series = [
        ("G777", "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/g777/ppi"),
        ("HQTI", "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/hqti/sppi")
    ]

    # Testing to always trigger
    testing = True

    # Get Settings
    mei_settings = settings()
    last_processed = mei_settings.lastProcessed_Get()

    # Check if the data has been updated today, if not, loop through series
    today = date.today().strftime("%d %B %Y")
    if not last_processed == today or testing:
        for dataset in series:
            if dataset[0] != "Example" and dataset[0] != "":
                datasets(dataset, mei_settings)  
        mei_settings.lastProcessed_Update()

class datasets:
    def __init__(self, series, mei_settings):
        self.mei_settings = mei_settings
        series_id = series[0]
        series_url = series[1]

        self.dataset_info(series_id, series_url)
    
    def dataset_info(self, series_id, series_url):
        lastReleasedNoted, lastUpdatedNoted, nextUpdateNoted = self.mei_settings.seriesData_Get(series_id)
        
        response = requests.get(series_url)
        html = BeautifulSoup(response.text, "html.parser")
        
        # Get the current release date
        p_elements = html.find_all("p", class_="col col--md-12 col--lg-15 meta__item")
        for p_element in p_elements:
            p_type = p_element. find('span').text
            if p_type == "Release date: ":
                releaseDate = p_element.text.replace("Release date: ", "").replace("View previous versions", "").strip()

        if releaseDate != lastReleasedNoted:

            # Get the next release date
            p_elements = html.find_all("p", class_="col col--md-11 col--lg-15 meta__item")
            for p_element in p_elements:
                p_type = p_element. find('span').text
                if p_type == "Next release: ":
                    nextReleaseDate = p_element.text.replace("Next release: ", "").replace("View previous versions", "").strip()

        # Series Download Data
        series_context = json.loads(html.find('script' , type='application/ld+json').string)
        series_distribution = series_context["distribution"]
        for series_distro in series_distribution:
            if series_distro["encodingFormat"] == "CSV":
                self.download_dataset(series_id, "CSV", series_distro["contentUrl"], releaseDate, nextReleaseDate)
            elif series_distro["encodingFormat"] == "XLS":
                self.download_dataset(series_id, "XLS", series_distro["contentUrl"], releaseDate, nextReleaseDate)

    def download_dataset(self, series, format, url, lastRelease, nextRelease):
        self.mei_settings.seriesDataFolder_Check(series)
        self.mei_settings.seriesDataFormatFolder_Check(series, format)
        
        todayString = date.today().strftime("%d %B %Y")
        fn = todayString + "." + format
        seriesFolderPath = self.mei_settings.seriesFolderPath_Get()
        fp = os.path.join(seriesFolderPath, series, format, fn)
        with open(fp, 'wb') as file: 
            file.write(requests.get(url).content)

        # Check if the file has been downloaded successfully 
        if os.path.exists(fp) and os.path.getsize(fp) > 0: 
            self.mei_settings.dataset_update(series, lastRelease, nextRelease, None)
        else: 
            self.mei_settings.dataset_update(series, lastRelease, nextRelease, f"Failed to download {series} for format {format} on {todayString}")

class settings():
    settingsFilePath = "mei_settings.json"
    seriesFolderPath = "Series Data"
    def __init__(self):
        if os.path.isfile(self.settingsFilePath):
            self.readSettings()
            self.seriesFolder_Check()
        else:
            self.createSettings()
            self.seriesFolder_Check()

    def seriesFolderPath_Get(self):
        return self.seriesFolderPath

    def createSettings(self):
        templateSettings = {"Last Processed": "01 January 1900", "series": {"Example": {"Last Updated": "01 January 1900", "Last Downloaded": "01 January 1900", "Next Release": "01 January 1900"}}}
        with open(self.settingsFilePath, mode="w", encoding="utf-8") as write_file:
            json.dump(obj = templateSettings, fp = write_file, indent=4)

    def seriesFolder_Check(self):
        if os.path.isdir(self.seriesFolderPath) == False:
            try:
                os.mkdir(self.seriesFolderPath)
            except:
                print("Unable to make series data folder")

    def readSettings(self):
        with open(self.settingsFilePath, mode="r", encoding="utf-8") as read_file:
            self.settingsFile = json.load(read_file)

    def updateSettings(self):
        with open(self.settingsFilePath, mode="w", encoding="utf-8") as write_file:
            json.dump(obj = self.settingsFile, fp = write_file, indent=4)
        self.readSettings()

    def lastProcessed_Get(self):
        lastProcessed = self.settingsFile["Last Processed"]
        return lastProcessed
    
    def lastProcessed_Update(self):
        self.settingsFile["Last Processed"] = date.today().strftime("%d %B %Y")
        self.updateSettings()

    def seriesData_Get(self, series_id):
        if series_id not in self.settingsFile["series"]:
            self.seriesData_Add(series_id)

        series = self.settingsFile["series"][series_id]
        return series["Last Updated"], series["Last Downloaded"], series["Next Release"]
        
    def seriesData_Add(self, series_id):
        default_values = { "Last Updated": "01 January 1900", "Last Downloaded": "01 January 1900", "Next Release": "01 January 1900" }
        self.settingsFile["series"][series_id] = default_values
        self.updateSettings()

    def seriesDataFolder_Check(self, series_id):
        seriesDataFolder = os.path.join(self.seriesFolderPath, series_id)
        if os.path.isdir(seriesDataFolder) == False:
            os.mkdir(seriesDataFolder)

    def seriesDataFormatFolder_Check(self, series_id, format):
        seriesDataFormatFolder = os.path.join(self.seriesFolderPath, series_id, format)
        if os.path.isdir(seriesDataFormatFolder) == False:
            os.mkdir(seriesDataFormatFolder)

    def dataset_update(self, series, lastRelease, nextRelease, error):
        if error == None:
            self.settingsFile["series"][series]["Last Updated"] = lastRelease
            self.settingsFile["series"][series]["Next Release"] = nextRelease
            self.settingsFile["series"][series]["Last Downloaded"] = date.today().strftime("%d %B %Y")
        else:
            self.settingsFile["series"][series]["Last Download Error"] = None
        self.updateSettings()
main()