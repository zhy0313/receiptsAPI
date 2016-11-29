# APP SETUP
###############################################################################
from flask import Flask, jsonify, abort, make_response, request
app = Flask(__name__)

# DATA SETUP
###############################################################################

UsersDB, ReceiptsDB = {}, {}

class User(object):
    ID = 1

    def __init__(self,first,last=None,address=None):
        self.id = User.ID
        User.ID += 1
        self.first = first
        self.last = last
        self.address = address
        self.receipts = {}

    def printUser(self):
        print "user #:", self.id
        print "  ", self.id, self.first, self.last, self.address
        for r in self.receipts:
            print "    ", r.get_receipt()

class Receipt(object):
    ID = 1
    required = set(['merchant_name','category','image','grand_total','purchase_date','userID'])
    optional = set(['merchant_address','subtotal','tax','discount','tip'])
    fields = set(["ID","userID","merchant_name","merchant_address","category","image","subtotal","tax","discount","tip","grand_total","purchase_date"])

    def __init__(   # required data
                    self,merchant_name=None,category=None,image=None,grand_total=None,purchase_date=None,
                    # optional data
                    merchant_address=None,subtotal=None,tax=None,discount=None,tip=None,userID=None,
                    # alternate input method
                    data=None):
        self.ID = Receipt.ID
        Receipt.ID += 1

        if data:    # I know the repeated code is bad form, but just want to get something to you first
            self.merchant_name = data['merchant_name']
            self.merchant_address = data['merchant_address']
            self.category = data['category']
            self.image = data['image']
            self.subtotal = data['subtotal']
            self.tax = data['tax']
            self.discount = data['discount']
            self.tip = data['tip']
            self.grand_total = data['grand_total']
            self.purchase_date = data['purchase_date']
            self.userID = data['userID']
        else:
            self.merchant_name = merchant_name
            self.merchant_address = merchant_address
            self.category = category
            self.image = image
            self.subtotal = subtotal
            self.tax = tax
            self.discount = discount
            self.tip = tip
            self.grand_total = grand_total
            self.purchase_date = purchase_date
            self.userID = userID

    def getReceipt(self):
        return {"ID": self.ID,
                "userID": self.userID,
                "merchantName": self.merchant_name,
                "merchantAddress": self.merchant_address,
                "subtotal": self.subtotal,
                "tax": self.tax,
                "discount": self.discount,
                "tip": self.tip,
                "category": self.category,
                "imageURL": self.image,
                "grandTotal": self.grand_total,
                "purchaseDate": self.purchase_date}


def addReceipt(userID,receipt):
    UsersDB[userID].receipts[receipt.ID] = receipt
    receipt.userID = userID
    ReceiptsDB[receipt.ID] = receipt

# pre-populate with test data
def initData():
    UsersDB[1] = User('John','Smith','111 1st Street, NY, NY, 10001, US')
    UsersDB[2] = User('Eric','Johnson','53 Utica Ave, Suite #221, Chicago, IL, 60647, US')
    UsersDB[3] = User('Danielle','Blaine','221B Baker St, London, NW1 6XE, UK')

    addReceipt( 3, Receipt("merch1","categ1","image1",395,"date1") )
    addReceipt( 1, Receipt("merch2","categ2","image2",112,"date2") )

initData()

# ROUTES
###############################################################################

@app.route('/')
def index():
    return "welcome to itemize; go to route /receipts to see all"

""" CREATE RECEIPT
run with:
    curl http://localhost:5000/receipts/create -H "Content-Type: application/json" -X POST -d '{"merchant_name":"name","category":"categ","image":"url","grand_total":500,"purchase_date":"date","userID":1}'
"""
@app.route('/receipts/create', methods=['POST'])
def create_receipt():
    if not request.data:
        abort(400)

    data = request.get_json()

    # ensure presence of required data
    for key in Receipt.required:
        if key not in data:
            abort(400,"Please provide values for: " + "".join(Receipt.required))

    # check for optional fields
    for key in Receipt.optional:
        if key not in data:
            data[key] = None

    userID = data["userID"]
    receipt = Receipt(data=data)

    addReceipt(int(userID),receipt)

    return jsonify({receipt.ID: receipt.getReceipt()})

""" READ RECEIPT - returns receipt from ID in request, or all receipts if none provided
for all receipts, run with:
    curl http://localhost:5000/receipts/read
for specific receipt, run with:
    curl http://localhost:5000/receipts/read -H "Content-Type: application/json" -X GET -d '{"ID":5}'
"""
@app.route('/receipts/read', methods=['GET'])
def get_receipt():

    if not request.data or 'ID' not in request.data:
        output = {receipt.ID:receipt.getReceipt() for receipt in ReceiptsDB.values()}
        return jsonify({'message':'no ID provided => all receipts returned', 'data':output})

    data = request.get_json()

    if data['ID'] not in ReceiptsDB.keys():
        abort(404, 'no receipt exists for this ID')

    receipt = ReceiptsDB[data['ID']].getReceipt()
    return jsonify({receipt['ID']: receipt})

""" UPDATE RECEIPT
run with:
    curl http://localhost:5000/receipts/update -H "Content-Type: application/json" -X PUT -d '{"ID":1,"data":{"merchant_name":"name","category":"categ","image":"url","grand_total":500,"purchase_date":"date","userID":1}}'
"""
@app.route('/receipts/update', methods=['PUT'])
def update_receipt():

    if not request.data or 'ID' not in request.data or 'data' not in request.data:
        abort(400)

    data = request.get_json()
    ID = data['ID']
    if ID not in ReceiptsDB:
        abort(404, ID + " is not a valid receipt ID")

    for k in data['data'].keys():
        if k not in Receipt.fields:
            abort(400, k + " is not a valid receipt field")

    receipt = ReceiptsDB[ID].getReceipt()
    for k,v in data['data'].iteritems():
        receipt[k] = v
    ReceiptsDB[ID],oldUserID,newUserID = receipt, receipt['userID'], data['data']['userID']
    
    if oldUserID != newUserID:
        Users[oldUserID].receipts.pop(ID)
        if newUserID not in Users:
            abort(404, newUserID + " is not a valid User ID")
        else:
            Users[newUserID].receipts.append(receipt)

    return jsonify({ID: receipt})

""" DELETE RECEIPT given ID
run with:
    curl http://localhost:5000/receipts/delete -H "Content-Type: application/json" -X DELETE -d '{"ID":1}'
"""
@app.route('/receipts/delete', methods=['DELETE'])
def delete_receipt():

    if not request.data or 'ID' not in request.data:
        abort(400)

    data = request.get_json()
    ID = data['ID']

    if ID not in ReceiptsDB:
        abort(404, ID + " is not a valid Receipt ID")

    receipt = ReceiptsDB[ID].getReceipt()
    ReceiptsDB.pop(ID)
    UsersDB[receipt['userID']].receipts.pop(ID)

    return jsonify({"message":"Receipt with ID " + str(ID) + " successfully deleted",
                    "receipt": receipt})


# ERROR HANDLERS
###############################################################################

@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'Error':"Bad Request", 'Message':error.description}), 400)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'Error':"Resource Not Found",'Message':error.description}), 404)









