# APP SETUP
###############################################################################
from flask import Flask, jsonify, abort, make_response, request
app = Flask(__name__)

# DATA SETUP
###############################################################################

# initialize DBs
users_db, receipts_db = {}, {}

class User(object):
    _id = 1

    def __init__(self,first,last=None,address=None):
        self._id = User._id
        User._id += 1
        self.first = first
        self.last = last
        self.address = address
        self.receipts = {}

    def print_user(self):
        print "user #:", self.id
        print "  ", self.id, self.first, self.last, self.address
        for r in self.receipts:
            print "    ", r.get_receipt()

class Receipt(object):
    _id = 1
    required = set(['merchant_name','category','image','grand_total','purchase_date','user_id'])
    optional = set(['merchant_address','subtotal','tax','discount','tip'])
    fields = set(["_id","user_id","merchant_name","merchant_address","category","image","subtotal","tax","discount","tip","grand_total","purchase_date"])

    def __init__(   # required data
                    self,merchant_name=None,category=None,image=None,grand_total=None,purchase_date=None,
                    # optional data
                    merchant_address=None,subtotal=None,tax=None,discount=None,tip=None,user_id=None,
                    # alternate input method
                    data=None):
        self._id = Receipt._id
        Receipt._id += 1

        if data:    # repeated code = bad form
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
            self.user_id = data['user_id']
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
            self.user_id = user_id

    def get_receipt(self):
        return {"_id": self._id,
                "user_id": self.user_id,
                "merchant_name": self.merchant_name,
                "merchant_address": self.merchant_address,
                "subtotal": self.subtotal,
                "tax": self.tax,
                "discount": self.discount,
                "tip": self.tip,
                "category": self.category,
                "image": self.image,
                "grand_total": self.grand_total,
                "purchase_date": self.purchase_date}


def add_receipt(user_id,receipt):
    users_db[user_id].receipts[receipt._id] = receipt
    receipt.user_id = user_id
    receipts_db[receipt._id] = receipt

# pre-populate with test data
def init_data():
    users_db[1] = User('John','Smith','111 1st Street, NY, NY, 10001, US')
    users_db[2] = User('Eric','Johnson','53 Utica Ave, Suite #221, Chicago, IL, 60647, US')
    users_db[3] = User('Danielle','Blaine','221B Baker St, London, NW1 6XE, UK')

    add_receipt( 3, Receipt("merch1","categ1","image1",395,"date1") )
    add_receipt( 1, Receipt("merch2","categ2","image2",112,"date2") )

init_data()

# ROUTES
###############################################################################

@app.route('/')
def index():
    return "welcome to itemize; go to route /receipts to see all"

""" CREATE RECEIPT
run with:
    curl http://localhost:5000/receipts/create -H "Content-Type: application/json" -X POST -d '{"merchant_name":"name","category":"categ","image":"url","grand_total":500,"purchase_date":"date","user_id":1}'
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

    user_id = data["user_id"]
    if user_id not in users_db:
        abort(404, str(user_id) + " is not a valid User ID")
    
    receipt = Receipt(data=data)

    add_receipt(int(user_id),receipt)

    return jsonify({receipt._id: receipt.get_receipt()})

""" READ RECEIPT - returns receipt from _id in request, or all receipts if none provided
for all receipts, run with:
    curl http://localhost:5000/receipts/read
for specific receipt, run with:
    curl http://localhost:5000/receipts/read -H "Content-Type: application/json" -X GET -d '{"_id":5}'
"""
@app.route('/receipts/read', methods=['GET'])
def get_receipt():

    if not request.data or '_id' not in request.data:
        output = {_id:receipt.get_receipt() for _id,receipt in receipts_db.iteritems()}
        return jsonify({'message':'no _id provided => all receipts returned', 'data':output})

    data = request.get_json()

    if data['_id'] not in receipts_db.keys():
        abort(404, 'no receipt exists for this _id')

    receipt = receipts_db[data['_id']]
    return jsonify({receipt._id: receipt.get_receipt()})

""" UPDATE RECEIPT - modifies provided fields of receipt without touching un-provided fields
run with:
    curl http://localhost:5000/receipts/update -H "Content-Type: application/json" -X PUT -d '{"_id":1,"data":{"merchant_name":"merchU","category":"categU","image":"urlU","grand_total":500,"purchase_date":"dateU","user_id":1}}'
"""
@app.route('/receipts/update', methods=['PUT'])
def update_receipt():

    if not request.data or '_id' not in request.data or 'data' not in request.data or 'user_id' not in request.data['data']:
        abort(400)

    data = request.get_json()
    _id = data['_id']
    
    if _id not in receipts_db:
        abort(404, str(_id) + " is not a valid receipt _id")

    for k in data['data'].keys():
        if k not in Receipt.fields:
            abort(400, k + " is not a valid receipt field")

    receipt = receipts_db[_id]
    old_user_id, new_user_id = receipt.user_id, data['data']['user_id']

    if new_user_id not in users_db:
        abort(404, str(new_user_id) + " is not a valid User _id")
    
    for k,v in data['data'].iteritems():
        setattr(receipt, k, v)

    receipts_db[_id] = receipt

    users_db[old_user_id].receipts.pop(_id)
    users_db[new_user_id].receipts[_id] = receipt

    return jsonify({_id: receipt.get_receipt()})

""" DELETE RECEIPT given _id
run with:
    curl http://localhost:5000/receipts/delete -H "Content-Type: application/json" -X DELETE -d '{"_id":1}'
"""
@app.route('/receipts/delete', methods=['DELETE'])
def delete_receipt():

    if not request.data or '_id' not in request.data:
        abort(400)

    data = request.get_json()
    _id = data['_id']

    if _id not in receipts_db:
        abort(404, str(_id) + " is not a valid Receipt _id")

    receipt = receipts_db[_id]
    receipts_db.pop(int(_id))
    users_db[receipt.user_id].receipts.pop(_id)

    return jsonify({"message":"Receipt with _id " + str(_id) + " successfully deleted",
                    "receipt": receipt.get_receipt()})


# ERROR HANDLERS
###############################################################################

@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'Error':"Bad Request", 'Message':error.description}), 400)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'Error':"Resource Not Found",'Message':error.description}), 404)









