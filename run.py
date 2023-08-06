from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
import os

from flask_msearch import Search
from flask_login import LoginManager
from flask_migrate import Migrate

from datetime import datetime

import secrets
import os
from flask import render_template,session, request,redirect,url_for,flash,current_app, Response
from wtforms import Form, SubmitField,IntegerField,FloatField,StringField,TextAreaField,validators
from flask_wtf.file import FileField,FileRequired,FileAllowed

import cv2
from cvzone.HandTrackingModule import HandDetector
import cvzone
import csv 
import time
from random import random
from my_yolov6 import my_yolov6
import openai

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
app.config['SECRET_KEY']='hfouewhfoiwefoquw'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['UPLOADED_PHOTOS_DEST'] = os.path.join(basedir, 'static/images')
app.config['UPLOAD_FOLDER'] = "static"
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
patch_request_class(app)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
search = Search()
search.init_app(app)

migrate = Migrate(app, db)
with app.app_context():
    if db.engine.url.drivername == "sqlite":
        migrate.init_app(app, db, render_as_batch=True)
    else:
        migrate.init_app(app, db)

yolov6_model = my_yolov6("weights/best_ckpt.pt","cpu","data/data.yaml", 640, True)
openai.api_key = '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 '

# from saving_planet.admin import routes
# from saving_planet.carts import carts
# from saving_planet.customers import routes

def brands():
    brands = Brand.query.join(Addcenter, (Brand.id == Addcenter.brand_id)).all()
    return brands

def categories():
    categories = Category.query.join(Addcenter,(Category.id == Addcenter.category_id)).all()
    return categories

class Addcenter(db.Model):
    __seachbale__ = ['name','desc']
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_number = db.Column(db.String(11), nullable=False)
    email = db.Column(db.String(80), nullable=False)
    address = db.Column(db.Text, nullable=False)
    desc = db.Column(db.Text, nullable=False)
    pub_date = db.Column(db.DateTime, nullable=False,default=datetime.utcnow)

    category_id = db.Column(db.Integer, db.ForeignKey('category.id'),nullable=False)
    category = db.relationship('Category',backref=db.backref('categories', lazy=True))

    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'),nullable=False)
    brand = db.relationship('Brand',backref=db.backref('brands', lazy=True))

    image_1 = db.Column(db.String(150), nullable=False, default='image1.jpg')
    image_2 = db.Column(db.String(150), nullable=False, default='image2.jpg')
    image_3 = db.Column(db.String(150), nullable=False, default='image3.jpg')

    def __repr__(self):
        return '<Post %r>' % self.name


class Brand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)

    def __repr__(self):
        return '<Brand %r>' % self.name
    

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)

    def __repr__(self):
        return '<Catgory %r>' % self.name


db.create_all()

class Addcenters(Form):
    name = StringField('Name', [validators.DataRequired()])
   
    address = TextAreaField('Address', [validators.DataRequired()])

    phone_number = StringField('Hotline', [validators.DataRequired()])

    email = StringField('Email', [validators.DataRequired()])

    description = TextAreaField('Description', [validators.DataRequired()])

    image_1 = FileField('Image 1', validators=[FileRequired(), FileAllowed(['jpg','png','gif','jpeg']), 'Images only please'])
    image_2 = FileField('Image 2', validators=[FileRequired(), FileAllowed(['jpg','png','gif','jpeg']), 'Images only please'])
    image_3 = FileField('Image 3', validators=[FileRequired(), FileAllowed(['jpg','png','gif','jpeg']), 'Images only please'])

#Game Page
@app.route('/game')
def game():
    return render_template('game.html')
@app.route('/playgame/<int:id>')
def play_game(id):
    return render_template('playgame.html', id=id)
@app.route('/video/<int:id>')
def video_feed(id):
    return Response(process_video(num=id), mimetype='multipart/x-mixed-replace; boundary=frame')

#Home Page
@app.route("/", methods=['GET', 'POST'])
def classify_garbage():
    if request.method == "POST":
        try:
            image = request.files['file']
            if image:
                path_to_save = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
                print("Save = ", path_to_save)
                image.save(path_to_save)
                frame = cv2.imread(path_to_save)
                frame, ndet = yolov6_model.infer(frame, conf_thres=0.6, iou_thres=0.45)
                if ndet!=0:
                    cv2.imwrite(path_to_save, frame)
                    print(0)
                    return render_template("home.html", user_image = image.filename , rand = str(random()),
                                           msg="Tải file lên thành công", ndet = ndet)
                else:
                    return render_template('home.html', msg='Không nhận diện được vật thể', ndet=ndet)
            else:
                return render_template('home.html', msg='Hãy chọn file để tải lên')
        except Exception as ex:
            print(ex)
            return render_template('home.html', msg='Không nhận diện được vật thể')
    else:
        return render_template('home.html')
    
#Chatbot Page
@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")

#Chatbot API
@app.route("/api", methods=["POST"])
def api():
    message = request.json.get("message")
    completion = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": message}
    ]
    )
    if completion.choices[0].message!=None:
        return completion.choices[0].message

    else :
        return 'Failed to Generate response!'

#Recycle Centers Page
@app.route('/centers')
def center():
    page = request.args.get('page',1, type=int)
    centers = Addcenter.query.order_by(Addcenter.id.desc()).paginate(page=page, per_page=8)
    return render_template('centers/index.html', centers=centers,brands=brands(),categories=categories())

@app.route('/result')
def result():
    searchword = request.args.get('q')
    centers = Addcenter.query.msearch(searchword, fields=['name','desc'] , limit=6)
    return render_template('centers/result.html',centers=centers,brands=brands(),categories=categories())

@app.route('/center/<int:id>')
def single_page(id):
    center = Addcenter.query.get_or_404(id)
    return render_template('centers/single_page.html',center=center,brands=brands(),categories=categories())


@app.route('/brand/<int:id>')
def get_brand(id):
    page = request.args.get('page',1, type=int)
    get_brand = Brand.query.filter_by(id=id).first_or_404()
    brand = Addcenter.query.filter_by(brand=get_brand).paginate(page=page, per_page=8)
    return render_template('centers/index.html',brand=brand,brands=brands(),categories=categories(),get_brand=get_brand)


@app.route('/categories/<int:id>')
def get_category(id):
    page = request.args.get('page',1, type=int)
    get_cat = Category.query.filter_by(id=id).first_or_404()
    get_cat_prod = Addcenter.query.filter_by(category=get_cat).paginate(page=page, per_page=8)
    return render_template('centers/index.html',get_cat_prod=get_cat_prod,brands=brands(),categories=categories(),get_cat=get_cat)


@app.route('/addbrand',methods=['GET','POST'])
def addbrand():
    if request.method =="POST":
        getbrand = request.form.get('brand')
        brand = Brand(name=getbrand)
        db.session.add(brand)
        flash(f'The brand {getbrand} was added to your database','success')
        db.session.commit()
        return redirect(url_for('addbrand'))
    return render_template('centers/addbrand.html', title='Add brand',brands='brands')

@app.route('/updatebrand/<int:id>',methods=['GET','POST'])
def updatebrand(id):
    if request.method =="POST":
        updatebrand.name = brand
        flash(f'The brand {updatebrand.name} was changed to {brand}','success')
        db.session.commit()
        return redirect(url_for('brands'))
    brand = updatebrand.name
    return render_template('centers/addbrand.html', title='Udate brand',brands='brands',updatebrand=updatebrand)


@app.route('/deletebrand/<int:id>', methods=['GET','POST'])
def deletebrand(id):
    brand = Brand.query.get_or_404(id)
    if request.method=="POST":
        db.session.delete(brand)
        flash(f"The brand {brand.name} was deleted from your database","success")
        db.session.commit()
        return redirect(url_for('admin'))
    flash(f"The brand {brand.name} can't be  deleted from your database","warning")
    return redirect(url_for('admin'))

@app.route('/addcat',methods=['GET','POST'])
def addcat():
    if request.method =="POST":
        getcat = request.form.get('category')
        category = Category(name=getcat)
        db.session.add(category)
        flash(f'The brand {getcat} was added to your database','success')
        db.session.commit()
        return redirect(url_for('addcat'))
    return render_template('centers/addbrand.html', title='Add category')


@app.route('/updatecat/<int:id>',methods=['GET','POST'])
def updatecat(id):
    if 'email' not in session:
        flash('Login first please','danger')
        return redirect(url_for('login'))
    updatecat = Category.query.get_or_404(id)
    category = request.form.get('category')  
    if request.method =="POST":
        updatecat.name = category
        flash(f'The category {updatecat.name} was changed to {category}','success')
        db.session.commit()
        return redirect(url_for('categories'))
    category = updatecat.name
    return render_template('centers/addbrand.html', title='Update cat',updatecat=updatecat)



@app.route('/deletecat/<int:id>', methods=['GET','POST'])
def deletecat(id):
    category = Category.query.get_or_404(id)
    if request.method=="POST":
        db.session.delete(category)
        flash(f"The brand {category.name} was deleted from your database","success")
        db.session.commit()
        return redirect(url_for('admin'))
    flash(f"The brand {category.name} can't be  deleted from your database","warning")
    return redirect(url_for('admin'))


@app.route('/addcenter', methods=['GET','POST'])
def addcenter():
    form = Addcenters(request.form)
    brands = Brand.query.all()
    categories = Category.query.all()
    if request.method=="POST"and 'image_1' in request.files:
        name = form.name.data
        address = form.address.data
        phone_number = form.phone_number.data
        email = form.email.data
        desc = form.description.data
        brand = request.form.get('brand')
        category = request.form.get('category')
        image_1 = photos.save(request.files.get('image_1'), name=secrets.token_hex(10) + ".")
        image_2 = photos.save(request.files.get('image_2'), name=secrets.token_hex(10) + ".")
        image_3 = photos.save(request.files.get('image_3'), name=secrets.token_hex(10) + ".")
        addcenter = Addcenter(name=name,address=address,phone_number = phone_number, email=email, desc=desc,category_id=category,brand_id=brand,image_1=image_1,image_2=image_2,image_3=image_3)
        db.session.add(addcenter)
        flash(f'The center {name} was added in database','success')
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('centers/addcenter.html', form=form, title='Add a center', brands=brands,categories=categories)

@app.route('/updatecenter/<int:id>', methods=['GET','POST'])
def updatecenter(id):
    form = Addcenters(request.form)
    center = Addcenter.query.get_or_404(id)
    brands = Brand.query.all()
    categories = Category.query.all()
    brand = request.form.get('brand')
    category = request.form.get('category')
    if request.method =="POST":
        center.name = form.name.data 
        center.address = form.address.data
        center.phone_number = form.phone_number.data
        center.email = form.email.data
        center.desc = form.description.data
        center.category_id = category
        center.brand_id = brand
        if request.files.get('image_1'):
            try:
                os.unlink(os.path.join(current_app.root_path, "static/images/" + center.image_1))
                center.image_1 = photos.save(request.files.get('image_1'), name=secrets.token_hex(10) + ".")
            except:
                center.image_1 = photos.save(request.files.get('image_1'), name=secrets.token_hex(10) + ".")
        if request.files.get('image_2'):
            try:
                os.unlink(os.path.join(current_app.root_path, "static/images/" + center.image_2))
                center.image_2 = photos.save(request.files.get('image_2'), name=secrets.token_hex(10) + ".")
            except:
                center.image_2 = photos.save(request.files.get('image_2'), name=secrets.token_hex(10) + ".")
        if request.files.get('image_3'):
            try:
                os.unlink(os.path.join(current_app.root_path, "static/images/" + center.image_3))
                center.image_3 = photos.save(request.files.get('image_3'), name=secrets.token_hex(10) + ".")
            except:
                center.image_3 = photos.save(request.files.get('image_3'), name=secrets.token_hex(10) + ".")

        flash('The center was updated','success')
        db.session.commit()
        return redirect(url_for('admin'))
    form.name.data = center.name
    form.address.data = center.address
    form.phone_number.data = center.phone_number
    form.email.data = center.email
    form.description.data = center.desc
    brand = center.brand.name
    category = center.category.name
    return render_template('centers/addcenter.html', form=form, title='Update center',getcenter=center, brands=brands,categories=categories)

@app.route('/deletecenter/<int:id>', methods=['POST'])
def deletecenter(id):
    center = Addcenter.query.get_or_404(id)
    if request.method =="POST":
        try:
            os.unlink(os.path.join(current_app.root_path, "static/images/" + center.image_1))
            os.unlink(os.path.join(current_app.root_path, "static/images/" + center.image_2))
            os.unlink(os.path.join(current_app.root_path, "static/images/" + center.image_3))
        except Exception as e:
            print(e)
        db.session.delete(center)
        db.session.commit()
        flash(f'The center {center.name} was delete from your record','success')
        return redirect(url_for('admin'))
    flash(f'Can not delete the center','danger')
    return redirect(url_for('admin'))

# @app.route('/admin')
# def admin():
#     centers = Addcenter.query.all()
#     return render_template('admin/index.html', title='Admin page',centers=centers)

# @app.route('/brands')
# def brands():
#     brands = Brand.query.order_by(Brand.id.desc()).all()
#     return render_template('admin/brand.html', title='brands',brands=brands)


# @app.route('/categories')
# def categories():
#     categories = Category.query.order_by(Category.id.desc()).all()
#     return render_template('admin/brand.html', title='categories',categories=categories)

#Process Game
def process_video(num):
    cap = cv2.VideoCapture(0)
    cap.set(3, 1280)
    cap.set(4, 720)
    detector = HandDetector(detectionCon=0.7)

    # Import csv file data
    if num == 1:
        pathCSV = "quiz/Mcqs_1.csv"
    elif num == 2: 
        pathCSV = "quiz/Mcqs_2.csv"
    elif num == 3: 
        pathCSV = "quiz/Mcqs_3.csv"
    elif num == 4: 
        pathCSV = "quiz/Mcqs_4.csv"
    elif num == 5: 
        pathCSV = "quiz/Mcqs_5.csv"
    elif num == 6: 
        pathCSV = "quiz/Mcqs_6.csv"

    with open(pathCSV, newline='\n') as f:
        reader = csv.reader(f)
        dataAll = list(reader)[1:]

    mcqList = []
    for q in dataAll:
        mcqList.append(MCQ(q))
    #print("Total MCQ Objects Created:", len(mcqList))

    qNo = 0
    qTotal = len(dataAll)
    
    correct_width = 0
    incorrect_width = 0
    while True:
        success, img = cap.read()
        img = cv2.flip(img, 1)
        hands, img = detector.findHands(img, flipType=False)

        if qNo < qTotal:
            mcq = mcqList[qNo]

            img, bbox = cvzone.putTextRect(img, mcq.question, [150, 100], 2, 2, offset=50, border=5)
            img, bbox1 = cvzone.putTextRect(img, mcq.choice1, [150, 250], 2, 2, offset=50, border=5)
            img, bbox2 = cvzone.putTextRect(img, mcq.choice2, [750, 250], 2, 2, offset=50, border=5)
            img, bbox3 = cvzone.putTextRect(img, mcq.choice3, [150, 500], 2, 2, offset=50, border=5)
            img, bbox4 = cvzone.putTextRect(img, mcq.choice4, [750, 500], 2, 2, offset=50, border=5)

            if hands:
                lmList = hands[0]['lmList']
                cursor = lmList[8]
                length, info = detector.findDistance(lmList[8], lmList[12])
                
                if length < 35:
                    mcq.update(cursor, [bbox1, bbox2, bbox3, bbox4])
                    if mcq.userAns is not None:
                        time.sleep(0.3)
                        qNo += 1
        else:
            score = 0
            for mcq in mcqList:
                if mcq.answer == mcq.userAns:
                    score += 1
            score = round((score / qTotal)* 100, 2)
            img, _ = cvzone.putTextRect(img, "Quiz Completed", [250, 300], 2, 2, offset=50, border=5)
            img, _ = cvzone.putTextRect(img, f'Your Score: {score}%', [700, 300], 2, 2, offset=50, border=5)
        
        correct_answers = sum(mcq.isCorrect for mcq in mcqList[:qNo])
        incorrect_answers = qNo - correct_answers
        correct_width = int((correct_answers / qTotal) * 950)
        incorrect_width = int((incorrect_answers / qTotal) * 950)
        barValue = 150 + (950 // qTotal) * qNo
        cv2.rectangle(img, (150, 600), (150 + correct_width, 650), (0, 255, 0), cv2.FILLED)
        cv2.rectangle(img, (150 + correct_width, 600), (150 + correct_width + incorrect_width, 650), (0, 0, 255), cv2.FILLED)
        cv2.rectangle(img, (150, 600), (1100, 650), (255, 0, 255), 5)
        img, _ = cvzone.putTextRect(img, f'{round((qNo / qTotal) * 100)}%', [1130, 635], 2, 2, offset=16)
        ret, buffer = cv2.imencode('.jpg', img)
        yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'

class MCQ():
    def __init__(self, data):
        self.question = data[0]
        self.choice1 = data[1]
        self.choice2 = data[2]
        self.choice3 = data[3]
        self.choice4 = data[4]
        self.answer = int(data[5])

        self.userAns = None

    def update(self, cursor, bboxs):

        for x, bbox in enumerate(bboxs):
            x1, y1, x2, y2 = bbox
            if x1 < cursor[0] < x2 and y1 < cursor[1] < y2:
                self.userAns = x + 1
        if self.userAns is not None:
            self.isCorrect = self.userAns == self.answer

if __name__ =="__main__":
    app.run(debug=True)