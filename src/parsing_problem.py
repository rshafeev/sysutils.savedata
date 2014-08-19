
# -*- coding: utf- -*-
import json
import logging

class ParsingProblem(object):

    def __init__(self, problemClass, problemNumber):
        self.problemClass = problemClass
        self.problemNumber = problemNumber
    def toModel(self, problem):
      model = {}
      model["name"] = problem["name"]
      model["problemClass"] = problem["problemClass"]
      model["vehicleCapacity"] = problem["vehicleCapacity"]
      model["depots"] = []
      
      customers = []
      depots = []
      
      i = 1
      for c in problem["customers"]:
        customer = {}
        customer["index"] = i
        customer["lat"] = c["lat"]
        customer["lon"] = c["lon"]
        customer["demand"] = c["demand"]
        customers.append(customer)
        i = i + 1
      depot = {}
      depot["lat"] = problem["depot"]["lat"]
      depot["lon"] = problem["depot"]["lon"]
      depot["capacity"] = -1
      depots.append(depot)

      model["customers"] = customers
      model["depots"] = depots
      return model


    def parse(self):
      filePath = 'problems/' + self.problemClass  + '/' + self.problemNumber + '.vrp'
      logging.info('parsing file: %s', filePath)
      f = open(filePath, 'r')
      problem = {}
      problem["problemClass"] = self.problemClass
       
      while True:
           line = f.readline().strip()
           if line.find("EOF") == 0:
              break
           line = line.strip()
           if line.find("DIMENSION") == 0:
              problem["dimension"] = int(line[12:].strip())
              logging.info('dimension: %i',  problem["dimension"])
           
           if line.find("NAME") == 0: 
              problem["name"] = line[7:].strip()
              logging.info('Problem name: %s',  problem["name"])
           
           if line.find("TYPE") == 0: 
              problem["type"] = line[7:].strip()
              logging.info('Problem type: %s',  problem["type"])

           if line.find("CAPACITY") == 0: 
              problem["vehicleCapacity"] = int(line[11:].strip())
              logging.info('VehicleCapacity: %s',  problem["vehicleCapacity"])

           if line.find("NODE_COORD_SECTION") == 0: 
              i = 0
              problem["customers"] = []
              while i < problem["dimension"]:
                  line = f.readline().strip()
                  customer = {}
                  ind1 = line.find(' ', 1)
                  ind2 = line.find(' ', ind1 +1)
                  lat  = line[ind1: ind2].rstrip()
                  lon  = line[ind2:].rstrip()
                  customer["lat"] = lat
                  customer["lon"] = lon
                  problem["customers"].append(customer)
                  i = i + 1
            
           if line.find("DEMAND_SECTION") == 0:
               i = 0
               while i < problem["dimension"]:
                  line = f.readline().strip()
                  ind = line.find(' ', 1)
                  id  = line[:ind].rstrip()
                  demand  = line[ind:].strip()
                  customer = problem["customers"][int(id) - 1]
                  customer["demand"] = demand
                  i = i + 1

           if line.find("DEPOT_SECTION") == 0: 
              line = f.readline().strip()
              id = int(line)
              node  = problem["customers"][int(id) - 1]
              problem["depot"] = node
              problem["customers"].remove(node)
           
      f.close()
      return problem

