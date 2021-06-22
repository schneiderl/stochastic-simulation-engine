from Scheduler import Scheduler
from Event import Event
from Entity import Entity
from Resource import Resource
from random import randrange
import numpy as np
from EntitySet import EntitySet


sch = Scheduler()



class CustomerGroup(Entity):
	def __init__(self, name, groupSize):
		super().__init__(name)
		self.groupSize = groupSize
		if groupSize == 1:
			self.tableType = 'Balcony'
		if groupSize == 2:
			self.tableType = 'TableForTwo'
		if groupSize > 2:
			self.tableType = 'TableForFour'

	def setTableType(self, tableType):
		self.tableType = tableType

	def getTableType(self):
		return self.tableType

class CustomerArrival(Event):
	def executeEvent(self, descriptors, model, groupSize):
		### chose one of the queues, pay and order
		self.recordAmountOfClientsInTotal(model, 	groupSize)

		customerGroup = model.createEntity("CustomerGroup", descriptors.entities, {'groupSize': groupSize})
		
		if model.getQueueSize("cashRegister1") > model.getQueueSize("cashRegister2"):
			model.insertInQueue("cashRegister2", customerGroup)
			if model.resources["Cashier2"].isAvailable():
				model.scheduleNow("CashierServiceStart", descriptors.events, {'cashierName': "Cashier2"})
		else:
			model.insertInQueue("cashRegister1", customerGroup)
			if model.resources["Cashier1"].isAvailable():
				model.scheduleNow("CashierServiceStart", descriptors.events, {'cashierName': "Cashier1"})

		if model.getTime() < 180.0:
			#generate new customers
			nextCustomerGroupSize = randrange(4)+1
			timeToNextArrival = np.random.exponential(3)
			model.scheduleIn("CustomerArrival", timeToNextArrival, descriptors.events, {'groupSize': nextCustomerGroupSize})
	
	def recordAmountOfClientsInTotal(self, model, groupSize):
		model.statistical.increaseDictLikeStatistic("Total number of people that ate at the restaurant:", groupSize)
	def recordStatistics(self, model):
		model.statistical.increaseDictLikeStatistic("Total Number of Groups of customers that arrived", 1)


class CashierServiceStart(Event):
	def executeEvent(self, descriptors, model, cashierName):
		if model.resources[cashierName].allocate(1):
			group = ""
			if cashierName == "Cashier1":
				group = model.popFromQueue("cashRegister1")
			else:
				group = model.popFromQueue("cashRegister2")

			timeToNextEvent = np.random.normal(8,2)
			model.scheduleIn("CashierServiceEnd", timeToNextEvent, descriptors.events, {'cashierName': cashierName, 'group': group})
	
	def recordStatistics(self, model):
		model.statistical.increaseDictLikeStatistic("Amount of clients that went through cashiers", 1)

class CashierServiceEnd(Event):
	def executeEvent(self, descriptors, model, cashierName, group):
		model.resources[cashierName].release(1)
		if cashierName == 'Cashier1':
			if model.isQueueEmpty("cashRegister1") == False:
				model.scheduleNow("CashierServiceStart", descriptors.events, {'cashierName': "Cashier1"})
		else:
			if model.isQueueEmpty("cashRegister2") == False:
				model.scheduleNow("CashierServiceStart", descriptors.events, {'cashierName': "Cashier2"})

		print("queued group, " + group.getTableType() + ': ' + str(group.getId()))
		model.insertInQueue(group.getTableType(), group)
		if model.resources[group.getTableType()].isAvailable():
			model.scheduleNow("SitCustomerWaiting", descriptors.events, {'group': model.popFromQueue(group.getTableType())})

		model.insertInQueue("Kitchen", group)

		if model.resources['Cook'].isAvailable():
			model.scheduleNow("NewOrderStart", descriptors.events, {})
	

	# def recordStatistics(self, model):
	# 	model.statistical.increaseDictLikeStatistic("Amount of clients ended the cashier service", 1)

class NewOrderStart(Event):
	def executeEvent(self, descriptors, model):
		if model.resources['Cook'].allocate(1):
		 	group = model.popFromQueue('Kitchen')
		 	timeToNextEvent = np.random.normal(14,5)
		 	model.scheduleIn("NewOrderEnd", timeToNextEvent,  descriptors.events, {'group':group})

	def recordStatistics(self, model):
		model.statistical.increaseDictLikeStatistic("Amount of registered orders:", 1)

class NewOrderEnd(Event):
	def executeEvent(self, descriptors, model, group):
		#customer has to be seated to start eating right away, otherwise it needs to wait for the delivery
		model.resources['Cook'].release(1)
		if model.isEntityInQueueById('SeatedWaiting', group.getId()):
			model.scheduleNow("CustomerEats", descriptors.events, {'group': group})
		else:
			model.insertInQueue('OrderWaitingForDelivery', group)
			#print('Finished Order:' +  str(group.getId()))

		if model.isQueueEmpty('Kitchen') == False:
			model.scheduleNow("NewOrderStart", descriptors.events, {})

	# def recordStatistics(self, model):
	# 	model.statistical.increaseDictLikeStatistic("Amount of finished orders:", 1)


class CustomerEats(Event):
	def executeEvent(self, descriptors, model, group):
		print("customer eating: " + str(group.getId()))
		model.removeFromQueueById('SeatedWaiting', group.getId())
		model.insertInQueue('SeatedEating', group)
		timeToNextEvent = np.random.normal(20,8)
		model.scheduleIn("CustomerLeaving", timeToNextEvent,  descriptors.events, {'group':group})

	# def recordStatistics(self, model):
	# 	model.statistical.increaseDictLikeStatistic("Customers that ate", 1)

class CustomerLeaving(Event):
	def executeEvent(self, descriptors, model, group):
		print("customer leaving:" + str(group.getId()))
		model.removeFromQueueById('SeatedEating', group.getId())
		model.resources[group.getTableType()].release(1)
		if model.isQueueEmpty(group.getTableType()) == False:
			print("seating customer after customer left")
			model.scheduleNow("SitCustomerWaiting", descriptors.events, {'group': model.popFromQueue(group.getTableType())})

	# def recordStatistics(self, model):
	# 	model.statistical.increaseDictLikeStatistic("Groups of customers left the restaurant", 1)


class SitCustomerWaiting(Event):
	def executeEvent(self, descriptors, model, group):
		if model.resources[group.getTableType()].isAvailable():
			 model.resources[group.getTableType()].allocate(1)
			 model.insertInQueue('SeatedWaiting', group)
			 if model.isEntityInQueueById('OrderWaitingForDelivery', group.getId()):
			 	print("order is ready - go right to eating")
			 	model.scheduleNow("CustomerEats", descriptors.events, {'group': group})
		else:
			model.insertInQueue(group.getTableType(), group)

	# def recordStatistics(self, model):
	# 	model.statistical.increaseDictLikeStatistic("Groups of customers that sat on tables", 1)

				



sch.defineResourceSpecialization('Cashier', Resource)
sch.defineResourceSpecialization('Table', Resource)
sch.defineResourceSpecialization('Cook', Resource)


sch.defineEntitySetSpecialization("cashRegister1", EntitySet)
sch.defineEntitySetSpecialization("cashRegister2", EntitySet)


sch.defineEntitySetSpecialization("Balcony", EntitySet)
sch.defineEntitySetSpecialization("TableForTwo", EntitySet)
sch.defineEntitySetSpecialization("TableForFour", EntitySet)

sch.defineEntitySetSpecialization("Kitchen", EntitySet)

sch.defineEntitySetSpecialization("SeatedWaiting", EntitySet)
sch.defineEntitySetSpecialization("SeatedEating", EntitySet)

sch.defineEntitySetSpecialization("UnseatedWaiting", EntitySet)


sch.initializeQueue("cashRegister1")
sch.initializeQueue("cashRegister2")

sch.initializeQueue("Balcony")
sch.initializeQueue("TableForTwo")
sch.initializeQueue("TableForFour")

sch.initializeQueue("Kitchen")

sch.initializeQueue("SeatedWaiting")
sch.initializeQueue("SeatedEating")

sch.initializeQueue("OrderWaitingForDelivery")


sch.createResource("Cashier", "Cashier1", 1)
sch.createResource("Cashier", "Cashier2", 1)
sch.createResource("Cook", "Cook", 3)


sch.createResource("Table", "Balcony", 6)
sch.createResource("Table", "TableForTwo", 4)
sch.createResource("Table", "TableForFour", 4)


sch.defineEventSpecialization('CustomerArrival', CustomerArrival)
sch.defineEventSpecialization('CashierServiceStart', CashierServiceStart)
sch.defineEventSpecialization('CashierServiceEnd', CashierServiceEnd)
sch.defineEventSpecialization('NewOrderStart', NewOrderStart)
sch.defineEventSpecialization('NewOrderEnd', NewOrderEnd)
sch.defineEventSpecialization('CustomerEats', CustomerEats)
sch.defineEventSpecialization('CustomerLeaving', CustomerLeaving)
sch.defineEventSpecialization('SitCustomerWaiting', SitCustomerWaiting)

sch.defineEntitySpecialization('CustomerGroup', CustomerGroup)

sch.scheduleNow('CustomerArrival', {'groupSize': 1})

sch.simulate()


#print("finished")