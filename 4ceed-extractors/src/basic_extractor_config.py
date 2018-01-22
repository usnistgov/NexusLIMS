# name to show in rabbitmq queue list
extractorName="new.basic.extractorPython3"

# URL to be used for connecting to rabbitmq
#rabbitmqURL = "amqp://guest:guest@localhost/%2f"
rabbitmqURL="amqp://guest:guest@localhost:5672/%2f"
#rabbitmqURL="amqp://guest:guest@***REMOVED***:5672/%2f"

# name of rabbitmq exchange
rabbitmqExchange="clowder"
playserverKey='***REMOVED***'

# type of files to process
messageType='*.file.image.#'


# trust certificates, set this to false for self signed certificates
sslVerify=False
