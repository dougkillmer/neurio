#! /usr/bin/env python
# -*- coding: utf-8 -*-
########################################
# Copyright (c) 2015 Doug Killmer

import indigo
import os
import random
import sys
import time

########################################
# NEURIO API
########################################

import base64
import urllib
import urllib2
import json
import urlparse
import datetime

class TokenProvider(object):
    __key = None
    __secret = None
    __token = None

    def __init__(self, key, secret):
        self.__key = key
        self.__secret = secret

        if self.__key is None or self.__secret is None:
            raise ValueError("Key and secret must be set.")

    def get_token(self):
        if self.__token is not None:
            return self.__token

        url = "https://api.neur.io/v1/oauth2/token"
        credentials = base64.b64encode(":".join([self.__key, self.__secret]))
        headers = {"Authorization": " ".join(["Basic", credentials])}
        param = {"grant_type": "client_credentials"}

        data = urllib.urlencode(param)
        request = urllib2.Request(url, data, headers)
        response = urllib2.urlopen(request)
        parsed_json = json.loads(response.read())
        access_token = parsed_json['access_token']
        return access_token

class Client(object):
    __token = None

    def __init__(self, token_provider):
        self.__token = token_provider.get_token()

    def __gen_headers(self):
        headers = {"Authorization": " ".join(["Bearer", self.__token])}
        return headers

    def __append_url_params(self, url, params):
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update(params)
        url_parts[4] = urllib.urlencode(query)
        return urlparse.urlunparse(url_parts)

    def get_user_information(self):
        url = "https://api.neur.io/v1/users/current"
        headers = self.__gen_headers()
        headers["Content-Type"] = "application/json"
        data = None

        request = urllib2.Request(url, data, headers)
        response = urllib2.urlopen(request)
        parsed_json = json.loads(response.read())
        return parsed_json

    def get_samples_live_last(self, sensor_id):
        url = "https://api.neur.io/v1/samples/live/last"
        headers = self.__gen_headers()
        headers["Content-Type"] = "application/json"
        params = {"sensorId": sensor_id}
        url = self.__append_url_params(url, params)
        data = None

        request = urllib2.Request(url, data, headers)
        response = urllib2.urlopen(request)
        parsed_json = json.loads(response.read())
        return parsed_json

    def get_samples_live(self, sensor_id):
        url = "http://" + sensor_id + "/current-sample"
        data = None

        request = urllib2.Request(url, data)
        response = urllib2.urlopen(request)
        parsed_json = json.loads(response.read())
        return parsed_json

    def get_samples_stats(self, sensor_id, start, granularity, end=None, frequency=None, per_page=None, page=None):
        url = "https://api.neur.io/v1/samples/stats"
        headers = self.__gen_headers()
        headers["Content-Type"] = "application/json"
        params = {
            "sensorId": sensor_id,
            "start": start,
            "granularity": granularity
        }
        if end:
            params["end"] = end
        if frequency:
            params["frequency"] = frequency
        if per_page:
            params["perPage"] = per_page
        if page:
            params["page"] = page
        url = self.__append_url_params(url, params)
        data = None

        request = urllib2.Request(url, data, headers)
        response = urllib2.urlopen(request)
        parsed_json = json.loads(response.read())
        return parsed_json
        
    def get_appliances(self, location_id):
        url = "https://api.neur.io/v1/appliances"
        headers = self.__gen_headers()
        headers["Content-Type"] = "application/json"
        params = {
            "locationId": location_id,
        }
        url = self.__append_url_params(url, params)
        data = None

        request = urllib2.Request(url, data, headers)
        response = urllib2.urlopen(request)
        parsed_json = json.loads(response.read())
        return parsed_json
        
    def get_appliance_stats(self, appliance_id, start, end, granularity, per_page=None, page=None, min_power=None):
        url = "https://api.neur.io/v1/appliances/stats"
        headers = self.__gen_headers()
        headers["Content-Type"] = "application/json"
        params = {
            "applianceId": appliance_id,
            "start": start,
            "end": end,
            "granularity": granularity       
        }
        if min_power:
            params["minPower"] = min_power
        if per_page:
            params["perPage"] = per_page
        if page:
            params["page"] = page
        url = self.__append_url_params(url, params)
        data = None

        request = urllib2.Request(url, data, headers)
        response = urllib2.urlopen(request)
        parsed_json = json.loads(response.read())
        return parsed_json

########################################
class Plugin(indigo.PluginBase):
    ########################################
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        self.debug = self.pluginPrefs["debugMode"]

    def __del__(self):
        indigo.PluginBase.__del__(self)

    ########################################
    def startup(self):
        self.debugLog(u"startup called")
        self._neurioSync()
        
    def shutdown(self):
        self.debugLog(u"shutdown called")    
       
    ######################################## 
    def _neurioSync(self):        
        # Neurio client
        client_id = str(self.pluginPrefs["clientID"])
        client_secret = str(self.pluginPrefs["clientSecret"])
        tp = TokenProvider(key=client_id, secret=client_secret)
        nc = Client(token_provider=tp)

        # Create folder for Neurio sensors and appliances
        if "Neurio" in indigo.devices.folders:
            folderId = indigo.devices.folders.getId("Neurio")
            self.debugLog(u"neurio folder found: " + str(folderId)) 
        else:
            neurioFolder = indigo.devices.folder.create("Neurio")
            folderId = neurioFolder.id
            self.debugLog(u"neurio folder created: " + str(folderId))  

        # List of devices available
        locations = []
        sensors = []
        appliances = []

        # For each location of current user
        user_info = nc.get_user_information()
        for location in user_info["locations"]:
            id = location["id"]
            name = location["name"]
            item = id, name
            locations.append(item)
                
            # Add sensors
            if bool(self.pluginPrefs["addSensors"]):
                for sensor in location["sensors"]:
                    id = sensor["sensorId"]
                    name = location["name"]
                    item = id, name
                    sensors.append(item)
        
        # Add appliances
        if bool(self.pluginPrefs["addAppliances"]):
            for location in locations:
                for appliance in nc.get_appliances(id):
                    id = appliance["id"]
                    name = appliance["label"]
                    item = id, name
                    appliances.append(item)                        
        
        # Sync devices
        self._neurioDevices(sensors, "neurioSensor", folderId)
        self._neurioDevices(appliances, "neurioAppliance", folderId)
              
    ######################################## 
    def _neurioDevices(self, devices, typeId, folderId):
        # Define device properties
        if typeId == "neurioSensor":
            description = "Neurio Sensor"
            properties = {'SupportsEnergyMeter':'true', 'SupportsEnergyMeterCurPower':'true'}
        if typeId == "neurioAppliance":
            description = "Neurio Appliance"
            properties = {'SupportsEnergyMeter':'false', 'SupportsEnergyMeterCurPower':'false'}
             
        # Loop through each Neurio device
        for device in devices:
            deviceId = device[0]
            deviceName = device[1]
            found = False
                    
            # Loop through each Indigo device  
            for dev in indigo.devices.iter("self"):
                if dev.deviceTypeId == typeId:
                    id = str(dev.id)
                    address = dev.address
                    folder = dev.folderId
                    
                    # Indigo device already exists
                    if address == deviceId:                           
                        found = True
                        self.debugLog(u"indigo device found: " + id + " (" + address + ")")
                        
                        # Move Neurio devices to folder
                        if folder != folderId:
                            indigo.device.moveToFolder(dev.id, value=folderId)
                            self.debugLog(u"indigo device moved to folder: " + id + " (" + str(folderId)) + ")"
                            break
            
            # Create new Indigo device
            if found == False:
                self.debugLog(u"indigo device not found, creating new device: " + deviceId)
                neurioDevice = indigo.device.create(protocol=indigo.kProtocol.Plugin,
                    address = deviceId,
                    name = deviceName, 
                    description = description, 
                    pluginId = "com.dougkillmer.indigoplugin.neurio",
                    deviceTypeId = typeId,
                    props = properties,
                    folder = folderId)
                indigo.device.displayInRemoteUI(neurioDevice, value=True)
                indigo.device.enable(neurioDevice, value=True)
                
                # Additional device settings
                if typeId == "neurioSensor":
                    indigo.device.resetEnergyAccumTotal(neurioDevice) 
                if typeId == "neurioAppliance":  
                    neurioDevice.updateStateOnServer("currentStatus", "off")
                    neurioDevice.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)   
                                         
        # Loop through each Indigo device       
        for dev in indigo.devices.iter("self"):
            if dev.deviceTypeId == typeId:                                    
                id = str(dev.id)
                address = dev.address
                found = False
                
                # Loop through each Neurio device
                for device in devices:
                    deviceId = device[0]                   
                    if deviceId == address:
                        self.debugLog(u"neurio device found: " + address + " (" + id + ")")
                        found = True
                
                # Remove missing devices
                if found == False:                        
                    self.debugLog(u"neurio device not found: " + address + " (" + id + "), removing indigo device")
                    indigo.device.delete(dev)        

    ########################################
    def _neurioRefresh(self, dev):       
        # Neurio Client
        client_id = str(self.pluginPrefs["clientID"])
        client_secret = str(self.pluginPrefs["clientSecret"])
        tp = TokenProvider(key=client_id, secret=client_secret)
        nc = Client(token_provider=tp)

        if dev.deviceTypeId == "neurioSensorLAN":
            # Get last sample from sensor
            sample = nc.get_samples_live(sensor_id=dev.address)
            channels = ""; consumption = ""; generation = ""; watts = ""
            for key, value in sample.iteritems():
                if key == "channels":
                    channels = sample[key]
            for channel in channels:
                for key, value in channel.iteritems():
                    if key == "type":
                        if channel[key] == "CONSUMPTION":
                            consumption = channel
                        if channel[key] == "GENERATION":
                            generation = channel
            for key, value in consumption.iteritems():
                if key == "p_W":
                    watts = consumption[key]
            consumption = watts

            # Update indigo server with stats    
            if "consumptionPower" in dev.states:           
                if consumption >= 1000:
                    watts = consumption*1./1000
                    wattsStr = "%.1f kW" % watts
                else:
                    wattsStr = "%d W" % consumption           
                dev.updateStateOnServer("curEnergyLevel", consumption, uiValue=wattsStr)
                dev.updateStateOnServer("consumptionPower", consumption, uiValue=wattsStr)
                self.debugLog(dev.name + " current load updated to " + wattsStr + " (" + str(consumption) + ")")
        
        if dev.deviceTypeId == "neurioSensor":
            # Get last sample from sensor
            sample = nc.get_samples_live_last(sensor_id=dev.address)       
            consumption = 0
            generation = 0
            for key, value in sample.iteritems():
                if key == "consumptionPower":
                    consumption = sample[key]  
                if key == "generationPower":
                    generation = sample[key]   
            
            # Update indigo server with last sample
            if "consumptionPower" in dev.states:           
                if consumption >= 1000:
                    watts = consumption*1./1000
                    wattsStr = "%.1f kW" % watts
                else:
                    wattsStr = "%d W" % consumption           
                dev.updateStateOnServer("curEnergyLevel", consumption, uiValue=wattsStr)
                dev.updateStateOnServer("consumptionPower", consumption, uiValue=wattsStr)
                self.debugLog(dev.name + " current load updated to " + wattsStr + " (" + str(consumption) + ")")
            if "generationPower" in dev.states:           
                if generation >= 1000:
                    watts = generation*1./1000
                    wattsStr = "%.1f kW" % (watts)
                else:
                    wattsStr = "%d W" % generation
                dev.updateStateOnServer("generationPower", generation, uiValue=wattsStr)
                self.debugLog(dev.name + " current generation updated to " + wattsStr+ " (" + str(generation) + ")")   

            # Get stats for sensor  
            update = int(self.pluginPrefs["updateSeconds"])      
            dt_format = "%Y-%m-%dT%H:%M:%SZ"
            delta = dev.energyAccumTimeDelta
            if delta < update:
                delta += update
            now = datetime.datetime.utcnow()
            startdate = (now - datetime.timedelta(seconds=delta)).strftime(dt_format)      
            stats = nc.get_samples_stats(sensor_id=dev.address, start=startdate, granularity="unknown")
            
            # Variables
            results = stats[0]
            start = ""
            end = ""
            consumptionWs = 0
            generationWs = 0
            for key, value in results.iteritems():
                if key == "start":
                    start = results[key]
                if key == "end":
                    end = results[key]
                if key == "consumptionEnergy":
                    consumptionWs = results[key]
                if key == "generationEnergy":
                    generationWs = results[key]
            consumption = consumptionWs*1./3600000
            generation = generationWs*1./3600000
            
            # Update indigo server with stats    
            if "consumptionEnergy" in dev.states:
                kwhStr = "%.3f kWh" % (consumption)           
                dev.updateStateOnServer("accumEnergyTotal", consumption, uiValue=kwhStr)
                dev.updateStateOnServer("consumptionEnergy", consumption, uiValue=kwhStr)   
                self.debugLog(dev.name + " total usage updated to " + kwhStr + " (" + str(consumptionWs) + ")")         
            if "generationEnergy" in dev.states:
                kwhStr = "%.3f kWh" % (generation)           
                dev.updateStateOnServer("generationEnergy", generation, uiValue=kwhStr) 
                self.debugLog(dev.name + " total generation updated to " + kwhStr + " (" + str(generationWs) + ")")
            if "statsBegin" in dev.states:
                dev.updateStateOnServer("statsBegin", start, uiValue=start)
            if "statsEnd" in dev.states:
                dev.updateStateOnServer("statsEnd", end, uiValue=end)
        
        if dev.deviceTypeId == "neurioAppliance":
            averagePower = ""
            timeOn = ""
            energy = ""
            usagePercentage = ""
            status = ""
            end = ""
            isConfirmed = ""
            
            dt_format = "%Y-%m-%dT%H:%M:%SZ"
            now = datetime.datetime.utcnow()
            startdate = (now - datetime.timedelta(hours=24)).strftime(dt_format)
            enddate = now.strftime(dt_format)            
            stats = nc.get_appliance_stats(appliance_id=dev.address, start=startdate, end=enddate, granularity="unknown", per_page="1", page="1")
            
            for item in stats:
                for key, value in item.iteritems():
                    if key == "averagePower":
                        averagePower = item[key]
                    if key == "timeOn":
                        timeOn = item[key]
                    if key == "energy":
                        energy = item[key]
                    if key == "usagePercentage":
                        usagePercentage = item[key]
                    if key == "lastEvent":
                        event = item[key]
                        for key, value in event.iteritems(): 
                            if key == "status":
                                status = event[key]
                            if key == "end":
                                end = event[key]
                            if key == "isConfirmed":
                                isConfirmed = event[key]

            appliance = dev.name
            appliance += " (" + str(dev.id) + ")"
            appliance += " " + str(startdate)
            appliance += " " + str(enddate)
            appliance += " " + str(averagePower)
            appliance += " " + str(timeOn)
            appliance += " " + str(energy)
            appliance += " " + str(usagePercentage)
            appliance += " " + str(status)
            appliance += " " + str(end)
            appliance += " " + str(isConfirmed)
            self.debugLog(appliance)
    
    #########################################        
    def _neurioRefreshAll(self):      
        # Refresh all devices     
        for dev in indigo.devices.iter("self"):  
            if dev.pluginId == "com.dougkillmer.indigoplugin.neurio":                               
                self._neurioRefresh(dev)

    ########################################
    def runConcurrentThread(self):
        try:
            while True:
                for dev in indigo.devices.iter("self"):
                    if not dev.enabled or not dev.configured:
                        continue
                                        
                    # Update devices with latest data
                    update = int(self.pluginPrefs["updateSeconds"])
                    self._neurioRefreshAll()
                    self.sleep(update)
                    
        except self.StopThread:
            pass  # Optionally catch the StopThread exception and do any needed cleanup.

    ########################################
    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        return (True, valuesDict)

    ########################################
    def deviceStartComm(self, dev):
        # Called when communication with the hardware should be established.
        # Here would be a good place to poll out the current states from the
        # meter. If periodic polling of the meter is needed (that is, it
        # doesn't broadcast changes back to the plugin somehow), then consider
        # adding that to runConcurrentThread() above.
        #self._refreshStatesFromHardware(dev)
        pass

    def deviceStopComm(self, dev):
        # Called when communication with the hardware should be shutdown.
        pass

    ########################################
    # General Action callback
    ########################################
    def actionControlGeneral(self, action, dev):
        ###### BEEP ######
        if action.deviceAction == indigo.kDeviceGeneralAction.Beep:
            # Beep the hardware module (dev) here:
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "beep request"))

        ###### ENERGY UPDATE ######
        elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyUpdate:
            # Request hardware module (dev) for its most recent meter data here:
            self._neurioRefresh(dev)

        ###### ENERGY RESET ######
        elif action.deviceAction == indigo.kDeviceGeneralAction.EnergyReset:
            # Request that the hardware module (dev) reset its accumulative energy usage data here:
            indigo.server.log(u"sent \"%s\" %s" % (dev.name, "energy usage reset"))           
            # And then tell Indigo to reset it by just setting the value to 0. This will automatically reset Indigo's time stamp for the accumulation.
            dev.updateStateOnServer("accumEnergyTotal", 0.0)

        ###### STATUS REQUEST ######
        elif action.deviceAction == indigo.kDeviceGeneralAction.RequestStatus:
            # Query hardware module (dev) for its current status here:
            self._neurioRefresh(dev)

    ########################################
  
