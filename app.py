import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, jsonify
from flask_mysqldb import MySQL
from flask_mail import Mail, Message as MailMessage
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date, datetime
import random
import string
import config

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['MYSQL_CHARSET'] = 'utf8mb4'

app.config['MAIL_SERVER'] = config.MAIL_SERVER
app.config['MAIL_PORT'] = config.MAIL_PORT
app.config['MAIL_USE_TLS'] = config.MAIL_USE_TLS
app.config['MAIL_USERNAME'] = config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = config.MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = config.MAIL_DEFAULT_SENDER

mysql = MySQL(app)
mail = Mail(app)


# ============================================
# DECORATORS
# ============================================
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') != role:
                flash('Access denied', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_customer_id():
    if session.get('role') != 'customer':
        return None
    cur = mysql.connection.cursor()
    cur.execute("SELECT CustomerID FROM Customer WHERE PersonID=%s", [session['person_id']])
    row = cur.fetchone()
    cur.close()
    return row['CustomerID'] if row else None


def get_provider_id():
    if session.get('role') != 'provider':
        return None
    cur = mysql.connection.cursor()
    cur.execute("SELECT ProviderID FROM Provider WHERE PersonID=%s", [session['person_id']])
    row = cur.fetchone()
    cur.close()
    return row['ProviderID'] if row else None


def get_wallet_balance(customer_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT Balance FROM Wallet WHERE CustomerID=%s", [customer_id])
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO Wallet (CustomerID, Balance) VALUES (%s, 0)", [customer_id])
        mysql.connection.commit()
        cur.close()
        return 0
    cur.close()
    return float(row['Balance'])


def generate_referral_code(customer_id):
    cur = mysql.connection.cursor()
    while True:
        code = 'PF' + str(customer_id) + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        cur.execute("SELECT 1 FROM Customer WHERE ReferralCode=%s", [code])
        if not cur.fetchone():
            cur.execute("UPDATE Customer SET ReferralCode=%s WHERE CustomerID=%s", [code, customer_id])
            mysql.connection.commit()
            cur.close()
            return code


def credit_wallet(customer_id, amount, description, booking_id=None):
    cur = mysql.connection.cursor()
    cur.execute("SELECT WalletID FROM Wallet WHERE CustomerID=%s", [customer_id])
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO Wallet (CustomerID, Balance) VALUES (%s, %s)", [customer_id, amount])
    else:
        cur.execute("UPDATE Wallet SET Balance = Balance + %s WHERE CustomerID=%s", [amount, customer_id])
    cur.execute("""
        INSERT INTO WalletTransaction (CustomerID, Amount, Type, Description, BookingID)
        VALUES (%s, %s, 'credit', %s, %s)
    """, [customer_id, amount, description, booking_id])
    mysql.connection.commit()
    cur.close()


def apply_coupon(code, order_amount):
    if not code:
        return 0, None
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT * FROM Coupon
        WHERE Code=%s AND IsActive=TRUE
          AND CURDATE() BETWEEN ValidFrom AND ValidTill
          AND (UsageLimit IS NULL OR UsedCount < UsageLimit)
    """, [code])
    coupon = cur.fetchone()
    cur.close()
    if not coupon:
        return 0, None
    if order_amount < float(coupon['MinOrderValue']):
        return 0, None
    if coupon['DiscountType'] == 'percent':
        discount = order_amount * float(coupon['DiscountValue']) / 100
        if coupon['MaxDiscount']:
            discount = min(discount, float(coupon['MaxDiscount']))
    else:
        discount = float(coupon['DiscountValue'])
    discount = min(discount, order_amount)
    return discount, coupon


def send_notification(person_id, subject, body, booking_id=None):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT Email FROM Person_Email WHERE PersonID=%s LIMIT 1", [person_id])
        row = cur.fetchone()
        email = row['Email'] if row else None
        status = 'pending'
        if config.MAIL_ENABLED and email:
            try:
                msg = MailMessage(subject=subject, recipients=[email], body=body)
                mail.send(msg)
                status = 'sent'
            except Exception as e:
                status = 'failed'
                print(f"[MAIL ERROR] {e}")
        cur.execute("""
            INSERT INTO NotificationLog (RecipientPersonID, RecipientEmail, Subject, Body, BookingID, Status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, [person_id, email, subject, body, booking_id, status])
        mysql.connection.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"[NOTIFICATION ERROR] {e}")
        return False


# ============================================
# ERROR HANDLERS
# ============================================
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ============================================
# PUBLIC ROUTES
# ============================================
@app.route('/')
def index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM Service_Category ORDER BY CategoryID")
    categories = cur.fetchall()
    cur.execute("""
        SELECT p.ProviderID, CONCAT(pe.FirstName,' ',pe.LastName) AS Name,
               p.AvgRating, p.ExperienceYears, l.City, st.ServiceName, ps.PricePerHour,
               (SELECT COUNT(*) FROM Review r WHERE r.ProviderID = p.ProviderID AND r.IsApproved = TRUE) AS ReviewCount
        FROM Provider p
        JOIN Person pe ON p.PersonID = pe.PersonID
        LEFT JOIN Location l ON pe.LocationID = l.LocationID
        JOIN Provider_Service ps ON p.ProviderID = ps.ProviderID
        JOIN Service_Type st ON ps.ServiceTypeID = st.ServiceTypeID
        WHERE p.IsVerified = TRUE
          AND (SELECT COUNT(*) FROM Review r WHERE r.ProviderID = p.ProviderID AND r.IsApproved = TRUE) > 0
        ORDER BY p.AvgRating DESC
        LIMIT 9
    """)
    providers = cur.fetchall()
    cur.close()
    return render_template('index.html', categories=categories, providers=providers)


@app.route('/search')
def search():
    category = request.args.get('category', '').strip()
    city = request.args.get('city', '').strip()
    service = request.args.get('service', '').strip()
    max_price_raw = request.args.get('max_price', '').strip()
    min_price_raw = request.args.get('min_price', '').strip()
    min_rating_raw = request.args.get('min_rating', '').strip()
    min_exp_raw = request.args.get('min_experience', '').strip()
    sort_by = request.args.get('sort', 'recommended').strip()

    if session.get('role') == 'customer' and any([category, city, service, max_price_raw, min_price_raw, min_rating_raw, min_exp_raw]):
        try:
            cid = get_customer_id()
            if cid:
                cur_h = mysql.connection.cursor()
                terms = ' | '.join(filter(None, [
                    f"cat:{category}" if category else '',
                    f"city:{city}" if city else '',
                    f"svc:{service}" if service else '',
                    f"max:{max_price_raw}" if max_price_raw else '',
                    f"min:{min_price_raw}" if min_price_raw else '',
                    f"rate:{min_rating_raw}" if min_rating_raw else '',
                    f"exp:{min_exp_raw}" if min_exp_raw else '',
                ]))
                cur_h.execute("""
                    UPDATE Customer
                    SET SearchHistory = CONCAT(COALESCE(SearchHistory,''), '|| ', %s)
                    WHERE CustomerID = %s
                """, [terms, cid])
                mysql.connection.commit()
                cur_h.close()
        except Exception:
            pass

    query = """
        SELECT DISTINCT p.ProviderID,
               CONCAT(pe.FirstName,' ',pe.LastName) AS Name,
               p.AvgRating, p.ExperienceYears,
               CASE WHEN (SELECT COUNT(*) FROM Review r WHERE r.ProviderID = p.ProviderID AND r.IsApproved = TRUE) > 0
                    THEN TRUE ELSE FALSE END AS HasReviews,
               p.Description,
               l.City, l.State, st.ServiceName, sc.CategoryName,
               ps.PricePerHour,
               (SELECT COUNT(*) FROM Review r WHERE r.ProviderID = p.ProviderID AND r.IsApproved = TRUE) AS ReviewCount
        FROM Provider p
        JOIN Person pe ON p.PersonID = pe.PersonID
        LEFT JOIN Location l ON pe.LocationID = l.LocationID
        JOIN Provider_Service ps ON p.ProviderID = ps.ProviderID
        JOIN Service_Type st ON ps.ServiceTypeID = st.ServiceTypeID
        JOIN Service_Category sc ON st.CategoryID = sc.CategoryID
        WHERE 1=1
    """
    params = []
    if category:
        query += " AND sc.CategoryName = %s"
        params.append(category)
    if city:
        query += " AND (l.City LIKE %s OR l.State LIKE %s)"
        params.append(f"%{city}%")
        params.append(f"%{city}%")
    if service:
        query += " AND (st.ServiceName LIKE %s OR sc.CategoryName LIKE %s)"
        params.append(f"%{service}%")
        params.append(f"%{service}%")
    if max_price_raw:
        try:
            query += " AND ps.PricePerHour <= %s"
            params.append(float(max_price_raw))
        except ValueError:
            pass
    if min_price_raw:
        try:
            query += " AND ps.PricePerHour >= %s"
            params.append(float(min_price_raw))
        except ValueError:
            pass
    if min_rating_raw:
        try:
            query += " AND p.AvgRating >= %s"
            params.append(float(min_rating_raw))
        except ValueError:
            pass
    if min_exp_raw:
        try:
            query += " AND p.ExperienceYears >= %s"
            params.append(int(min_exp_raw))
        except ValueError:
            pass

    if sort_by == 'rating':
        query += " ORDER BY p.AvgRating DESC"
    elif sort_by == 'experience':
        query += " ORDER BY p.ExperienceYears DESC"
    elif sort_by == 'price_low':
        query += " ORDER BY ps.PricePerHour ASC"
    elif sort_by == 'price_high':
        query += " ORDER BY ps.PricePerHour DESC"
    else:
        query += " ORDER BY p.AvgRating DESC, p.ExperienceYears DESC"

    cur = mysql.connection.cursor()
    cur.execute(query, params)
    results = cur.fetchall()
    cur.execute("SELECT * FROM Service_Category ORDER BY CategoryID")
    categories = cur.fetchall()
    cur.close()
    return render_template('search.html', results=results,
                           categories=categories, filters=request.args)


@app.route('/professional/<int:pid>')
def professional_detail(pid):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.*, pe.FirstName, pe.LastName, pe.Phone, pe.Age,
               l.City, l.State, l.Zip
        FROM Provider p
        JOIN Person pe ON p.PersonID = pe.PersonID
        LEFT JOIN Location l ON pe.LocationID = l.LocationID
        WHERE p.ProviderID = %s
    """, [pid])
    provider = cur.fetchone()
    if not provider:
        abort(404)

    cur.execute("""
        SELECT ps.ProviderServiceID, st.ServiceName, st.ServiceTypeID,
               st.Description, ps.PricePerHour, sc.CategoryName
        FROM Provider_Service ps
        JOIN Service_Type st ON ps.ServiceTypeID = st.ServiceTypeID
        JOIN Service_Category sc ON st.CategoryID = sc.CategoryID
        WHERE ps.ProviderID = %s
    """, [pid])
    services = cur.fetchall()

    cur.execute("""
        SELECT r.*, CONCAT(pe.FirstName,' ',pe.LastName) AS CustomerName
        FROM Review r
        JOIN Customer c ON r.CustomerID = c.CustomerID
        JOIN Person pe ON c.PersonID = pe.PersonID
        WHERE r.ProviderID = %s AND r.IsApproved = TRUE
        ORDER BY r.ReviewDate DESC LIMIT 10
    """, [pid])
    reviews = cur.fetchall()

    cur.execute("""
        SELECT ROUND(AVG(Rating),1) AS LiveAvg, COUNT(*) AS Cnt
        FROM Review WHERE ProviderID = %s AND IsApproved = TRUE
    """, [pid])
    stats = cur.fetchone()

    cur.execute("""
        SELECT AvailabilityID, AvailableDate, StartTime, EndTime, IsBooked
        FROM Availability
        WHERE ProviderID = %s AND AvailableDate >= CURDATE() AND IsBooked = FALSE
        ORDER BY AvailableDate, StartTime LIMIT 6
    """, [pid])
    slots = cur.fetchall()

    is_fav = False
    if session.get('role') == 'customer':
        cid = get_customer_id()
        if cid:
            cur.execute("SELECT 1 FROM Favorite WHERE CustomerID=%s AND ProviderID=%s", [cid, pid])
            is_fav = cur.fetchone() is not None

    cur.execute("SELECT Email FROM Person_Email WHERE PersonID = %s LIMIT 1", [provider['PersonID']])
    email_row = cur.fetchone()
    provider_email = email_row['Email'] if email_row else ''
    cur.close()

    return render_template('professional_detail.html',
                           provider=provider, services=services, reviews=reviews,
                           stats=stats, slots=slots, is_fav=is_fav,
                           provider_email=provider_email)


@app.route('/contact/<int:pid>')
def contact_provider(pid):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.ProviderID, CONCAT(pe.FirstName,' ',pe.LastName) AS Name,
               pe.Phone, l.City, l.State
        FROM Provider p
        JOIN Person pe ON p.PersonID = pe.PersonID
        LEFT JOIN Location l ON pe.LocationID = l.LocationID
        WHERE p.ProviderID = %s
    """, [pid])
    provider = cur.fetchone()
    if not provider:
        abort(404)
    cur.execute("SELECT Email FROM Person_Email WHERE PersonID = (SELECT PersonID FROM Provider WHERE ProviderID=%s) LIMIT 1", [pid])
    email_row = cur.fetchone()
    cur.close()
    return render_template('contact_provider.html',
                           provider=provider,
                           email=email_row['Email'] if email_row else 'N/A')


# ============================================
# FAVORITES
# ============================================
@app.route('/favorite/toggle/<int:pid>')
@login_required
def toggle_favorite(pid):
    if session['role'] != 'customer':
        flash('Only customers can save favorites', 'warning')
        return redirect(url_for('professional_detail', pid=pid))
    cid = get_customer_id()
    cur = mysql.connection.cursor()
    cur.execute("SELECT 1 FROM Favorite WHERE CustomerID=%s AND ProviderID=%s", [cid, pid])
    exists = cur.fetchone()
    if exists:
        cur.execute("DELETE FROM Favorite WHERE CustomerID=%s AND ProviderID=%s", [cid, pid])
        flash('Removed from favorites', 'info')
    else:
        cur.execute("INSERT INTO Favorite (CustomerID, ProviderID) VALUES (%s, %s)", [cid, pid])
        flash('Added to favorites', 'success')
    mysql.connection.commit()
    cur.close()
    return redirect(url_for('professional_detail', pid=pid))


@app.route('/favorites')
@login_required
def favorites():
    if session['role'] != 'customer':
        flash('Only customers have favorites', 'warning')
        return redirect(url_for('dashboard'))
    cid = get_customer_id()
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.ProviderID, CONCAT(pe.FirstName,' ',pe.LastName) AS Name,
               p.AvgRating, p.ExperienceYears, l.City,
               (SELECT COUNT(*) FROM Review r WHERE r.ProviderID = p.ProviderID AND r.IsApproved=TRUE) AS ReviewCount,
               f.AddedAt
        FROM Favorite f
        JOIN Provider p ON f.ProviderID = p.ProviderID
        JOIN Person pe ON p.PersonID = pe.PersonID
        LEFT JOIN Location l ON pe.LocationID = l.LocationID
        WHERE f.CustomerID = %s
        ORDER BY f.AddedAt DESC
    """, [cid])
    favs = cur.fetchall()
    cur.close()
    return render_template('favorites.html', favorites=favs)


# ============================================
# SEARCH HISTORY
# ============================================
@app.route('/my-searches')
@login_required
def my_searches():
    if session['role'] != 'customer':
        flash('Only customers have search history', 'warning')
        return redirect(url_for('dashboard'))
    cid = get_customer_id()
    cur = mysql.connection.cursor()
    cur.execute("SELECT SearchHistory FROM Customer WHERE CustomerID=%s", [cid])
    row = cur.fetchone()
    cur.close()
    raw = row['SearchHistory'] if row and row['SearchHistory'] else ''
    entries = [e.strip() for e in raw.split('||') if e.strip()]
    entries = list(reversed(entries))[:50]
    return render_template('my_searches.html', entries=entries)


@app.route('/my-searches/clear', methods=['POST'])
@login_required
def clear_searches():
    if session['role'] != 'customer':
        return redirect(url_for('dashboard'))
    cid = get_customer_id()
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Customer SET SearchHistory = NULL WHERE CustomerID=%s", [cid])
    mysql.connection.commit()
    cur.close()
    flash('Search history cleared', 'info')
    return redirect(url_for('my_searches'))


# ============================================
# NOTIFICATIONS
# ============================================
@app.route('/notifications')
@login_required
def notifications():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT * FROM NotificationLog
        WHERE RecipientPersonID = %s
        ORDER BY SentAt DESC LIMIT 50
    """, [session['person_id']])
    notifs = cur.fetchall()
    cur.close()
    return render_template('notifications.html', notifications=notifs)


# ============================================
# CHAT SYSTEM
# ============================================
@app.route('/chat')
@login_required
def chat_inbox():
    pid = session['person_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT DISTINCT
            CASE WHEN m.SenderID = %s THEN m.ReceiverID ELSE m.SenderID END AS OtherPersonID
        FROM Message m
        WHERE m.SenderID = %s OR m.ReceiverID = %s
    """, [pid, pid, pid])
    partners = cur.fetchall()

    conversations = []
    for p in partners:
        other_id = p['OtherPersonID']
        cur.execute("SELECT CONCAT(FirstName,' ',LastName) AS Name FROM Person WHERE PersonID=%s", [other_id])
        name_row = cur.fetchone()
        cur.execute("""
            SELECT Body, SentAt, SenderID, IsRead
            FROM Message
            WHERE (SenderID=%s AND ReceiverID=%s) OR (SenderID=%s AND ReceiverID=%s)
            ORDER BY SentAt DESC LIMIT 1
        """, [pid, other_id, other_id, pid])
        last = cur.fetchone()
        cur.execute("""
            SELECT COUNT(*) AS c FROM Message
            WHERE SenderID=%s AND ReceiverID=%s AND IsRead=FALSE
        """, [other_id, pid])
        unread = cur.fetchone()['c']
        conversations.append({
            'other_id': other_id,
            'name': name_row['Name'] if name_row else 'Unknown',
            'last_msg': last['Body'] if last else '',
            'last_time': last['SentAt'] if last else '',
            'unread': unread
        })
    cur.close()
    return render_template('chat_inbox.html', conversations=conversations)


@app.route('/chat/<int:other_person_id>', methods=['GET', 'POST'])
@login_required
def chat_with(other_person_id):
    pid = session['person_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT CONCAT(FirstName,' ',LastName) AS Name FROM Person WHERE PersonID=%s", [other_person_id])
    other = cur.fetchone()
    if not other:
        cur.close()
        abort(404)

    if request.method == 'POST':
        body = request.form.get('body', '').strip()
        if body:
            cur.execute("""
                INSERT INTO Message (SenderID, ReceiverID, Body)
                VALUES (%s, %s, %s)
            """, [pid, other_person_id, body])
            mysql.connection.commit()
            send_notification(other_person_id, f"New message from {session['username']}", body[:200])
        return redirect(url_for('chat_with', other_person_id=other_person_id))

    cur.execute("""
        UPDATE Message SET IsRead=TRUE
        WHERE SenderID=%s AND ReceiverID=%s
    """, [other_person_id, pid])

    cur.execute("""
        SELECT m.*, CONCAT(pe.FirstName,' ',pe.LastName) AS SenderName
        FROM Message m
        JOIN Person pe ON m.SenderID = pe.PersonID
        WHERE (m.SenderID=%s AND m.ReceiverID=%s)
           OR (m.SenderID=%s AND m.ReceiverID=%s)
        ORDER BY m.SentAt ASC
        LIMIT 200
    """, [pid, other_person_id, other_person_id, pid])
    messages = cur.fetchall()
    cur.close()
    return render_template('chat.html', messages=messages, other=other, other_person_id=other_person_id)


@app.route('/chat/message/<int:msg_id>/delete', methods=['POST'])
@login_required
def delete_message(msg_id):
    pid = session['person_id']
    cur = mysql.connection.cursor()
    cur.execute("SELECT SenderID FROM Message WHERE MessageID=%s", [msg_id])
    row = cur.fetchone()
    if not row:
        cur.close()
        flash('Message not found', 'danger')
        return redirect(url_for('chat_inbox'))
    if row['SenderID'] != pid:
        cur.close()
        flash('You can only delete your own messages', 'danger')
        return redirect(url_for('chat_inbox'))
    cur.execute("DELETE FROM Message WHERE MessageID=%s", [msg_id])
    mysql.connection.commit()
    cur.close()
    flash('Message deleted', 'info')
    other = request.form.get('other_person_id')
    if other:
        return redirect(url_for('chat_with', other_person_id=other))
    return redirect(url_for('chat_inbox'))


@app.route('/chat/start/<int:provider_id>')
@login_required
def chat_start(provider_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT PersonID FROM Provider WHERE ProviderID=%s", [provider_id])
    row = cur.fetchone()
    cur.close()
    if not row:
        flash('Provider not found', 'danger')
        return redirect(url_for('index'))
    return redirect(url_for('chat_with', other_person_id=row['PersonID']))


# ============================================
# COUPONS
# ============================================
@app.route('/coupons')
def coupons():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT * FROM Coupon
        WHERE IsActive=TRUE AND CURDATE() BETWEEN ValidFrom AND ValidTill
          AND (UsageLimit IS NULL OR UsedCount < UsageLimit)
        ORDER BY DiscountValue DESC
    """)
    coupons = cur.fetchall()
    cur.close()
    return render_template('coupons.html', coupons=coupons)


@app.route('/coupon/validate', methods=['POST'])
@login_required
def validate_coupon():
    if session['role'] != 'customer':
        return jsonify({'ok': False, 'message': 'Only customers can use coupons'})

    code = request.form.get('code', '').strip().upper()
    try:
        amount = float(request.form.get('amount', 0))
    except ValueError:
        return jsonify({'ok': False, 'message': 'Invalid amount'})

    discount, coupon = apply_coupon(code, amount)
    if coupon and discount > 0:
        return jsonify({
            'ok': True,
            'discount': round(discount, 2),
            'message': f'Coupon applied! You save Rs.{discount:.2f}',
            'code': coupon['Code']
        })
    return jsonify({'ok': False, 'message': 'Invalid or ineligible coupon'})


# ============================================
# WALLET
# ============================================
@app.route('/wallet')
@login_required
def wallet():
    if session['role'] != 'customer':
        flash('Only customers have wallets', 'warning')
        return redirect(url_for('dashboard'))
    cid = get_customer_id()
    balance = get_wallet_balance(cid)
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT * FROM WalletTransaction
        WHERE CustomerID = %s
        ORDER BY TxnDate DESC
        LIMIT 50
    """, [cid])
    txns = cur.fetchall()
    cur.close()
    return render_template('wallet.html', balance=balance, transactions=txns)


@app.route('/wallet/add', methods=['GET', 'POST'])
@login_required
def wallet_add():
    if session['role'] != 'customer':
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            if amount <= 0 or amount > 50000:
                raise ValueError
        except (ValueError, KeyError):
            flash('Enter a valid amount (1-50000)', 'danger')
            return redirect(url_for('wallet_add'))

        cid = get_customer_id()
        try:
            credit_wallet(cid, amount, 'Wallet top-up')
            flash(f'Rs.{amount:.2f} added to your wallet!', 'success')
            return redirect(url_for('wallet'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')

    return render_template('wallet_add.html')


# ============================================
# REFERRAL SYSTEM
# ============================================
@app.route('/referrals')
@login_required
def referrals():
    if session['role'] != 'customer':
        flash('Only customers have referrals', 'warning')
        return redirect(url_for('dashboard'))

    cid = get_customer_id()
    cur = mysql.connection.cursor()

    cur.execute("SELECT ReferralCode FROM Customer WHERE CustomerID=%s", [cid])
    row = cur.fetchone()
    if not row or not row['ReferralCode']:
        cur.close()
        code = generate_referral_code(cid)
    else:
        code = row['ReferralCode']

    cur.execute("""
        SELECT r.*, CONCAT(pe.FirstName,' ',pe.LastName) AS RefereeName
        FROM Referral r
        LEFT JOIN Customer c ON r.RefereeCustomerID = c.CustomerID
        LEFT JOIN Person pe ON c.PersonID = pe.PersonID
        WHERE r.ReferrerCustomerID = %s
        ORDER BY r.CreatedAt DESC
    """, [cid])
    my_referrals = cur.fetchall()

    cur.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN Status='completed' THEN 1 ELSE 0 END) AS completed,
               COALESCE(SUM(CASE WHEN Status='completed' THEN RewardAmount ELSE 0 END), 0) AS earned
        FROM Referral WHERE ReferrerCustomerID = %s
    """, [cid])
    stats = cur.fetchone()

    cur.close()
    return render_template('referrals.html',
                           code=code,
                           my_referrals=my_referrals,
                           stats=stats)


@app.route('/referrals/invite', methods=['POST'])
@login_required
def referral_invite():
    if session['role'] != 'customer':
        flash('Only customers can invite', 'warning')
        return redirect(url_for('dashboard'))

    email = request.form.get('email', '').strip().lower()
    if not email or '@' not in email:
        flash('Enter a valid email', 'danger')
        return redirect(url_for('referrals'))

    cid = get_customer_id()
    cur = mysql.connection.cursor()

    cur.execute("SELECT ReferralCode FROM Customer WHERE CustomerID=%s", [cid])
    row = cur.fetchone()
    code = row['ReferralCode'] if row and row['ReferralCode'] else generate_referral_code(cid)

    cur.execute("""
        SELECT 1 FROM Referral
        WHERE ReferrerCustomerID=%s AND RefereeEmail=%s AND Status='pending'
    """, [cid, email])
    if cur.fetchone():
        cur.close()
        flash('You have already invited this email', 'warning')
        return redirect(url_for('referrals'))

    cur.execute("""
        INSERT INTO Referral (ReferrerCustomerID, ReferralCode, RefereeEmail, Status, RewardAmount)
        VALUES (%s, %s, %s, 'pending', 100)
    """, [cid, code, email])
    mysql.connection.commit()
    cur.close()

    send_notification(session['person_id'],
                      f"Referral invite sent to {email}",
                      f"You invited {email}.")

    flash(f'Invite sent to {email}!', 'success')
    return redirect(url_for('referrals'))


@app.route('/referrals/claim/<code>')
def referral_claim(code):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.CustomerID, c.ReferralCode,
               CONCAT(p.FirstName,' ',p.LastName) AS Name
        FROM Customer c
        JOIN Person p ON c.PersonID = p.PersonID
        WHERE c.ReferralCode = %s
    """, [code])
    referrer = cur.fetchone()
    cur.close()

    if not referrer:
        flash('Invalid referral code', 'danger')
        return redirect(url_for('register'))

    session['referral_code'] = code
    return render_template('referral_claim.html', referrer=referrer, code=code)


# ============================================
# MULTI-SERVICE BOOKING
# ============================================
@app.route('/multi-book/<int:provider_id>', methods=['GET', 'POST'])
@login_required
def multi_book(provider_id):
    if session['role'] != 'customer':
        flash('Only customers can book', 'warning')
        return redirect(url_for('index'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT p.ProviderID, CONCAT(pe.FirstName,' ',pe.LastName) AS Name
        FROM Provider p
        JOIN Person pe ON p.PersonID = pe.PersonID
        WHERE p.ProviderID = %s
    """, [provider_id])
    provider = cur.fetchone()
    if not provider:
        cur.close()
        abort(404)

    cid = get_customer_id()
    wallet_balance = get_wallet_balance(cid)

    if request.method == 'POST':
        selected_services = request.form.getlist('service_type_id')
        date_val = request.form['date']
        time_val = request.form['time']
        emergency = 'emergency' in request.form
        coupon_code = request.form.get('coupon_code', '').strip().upper()
        pay_with_wallet = 'pay_wallet' in request.form

        if not selected_services:
            flash('Please select at least one service', 'warning')
            return redirect(url_for('multi_book', provider_id=provider_id))

        try:
            datetime.strptime(date_val, '%Y-%m-%d')
            datetime.strptime(time_val, '%H:%M')
        except ValueError:
            flash('Invalid date or time', 'danger')
            return redirect(url_for('multi_book', provider_id=provider_id))

        primary_service = int(selected_services[0])

        try:
            cur.execute("""
                INSERT INTO Booking (CustomerID, ProviderID, ServiceTypeID, BookingDate, BookingTime, IsEmergency)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [cid, provider_id, primary_service, date_val, time_val, emergency])
            booking_id = cur.lastrowid

            total = 0
            for sid in selected_services:
                cur.execute("""
                    SELECT PricePerHour FROM Provider_Service
                    WHERE ProviderID=%s AND ServiceTypeID=%s
                """, [provider_id, sid])
                pr = cur.fetchone()
                price = float(pr['PricePerHour']) if pr else 500
                total += price
                cur.execute("""
                    INSERT INTO Booking_Service (BookingID, ServiceTypeID, PricePerHour)
                    VALUES (%s, %s, %s)
                """, [booking_id, sid, price])

            discount, coupon_row = apply_coupon(coupon_code, total)
            if coupon_row and discount > 0:
                cur.execute("""
                    INSERT INTO Booking_Coupon (BookingID, CouponID, DiscountApplied)
                    VALUES (%s, %s, %s)
                """, [booking_id, coupon_row['CouponID'], discount])
                cur.execute("UPDATE Coupon SET UsedCount = UsedCount + 1 WHERE CouponID=%s", [coupon_row['CouponID']])
                cur.execute("""
                    UPDATE Booking SET DiscountApplied=%s, CouponCode=%s WHERE BookingID=%s
                """, [discount, coupon_row['Code'], booking_id])

            final_total = max(0, total - discount)
            cur.execute("UPDATE Booking SET TotalPrice=%s WHERE BookingID=%s", [final_total, booking_id])

            if pay_with_wallet:
                if wallet_balance >= final_total:
                    cur.execute("UPDATE Wallet SET Balance = Balance - %s WHERE CustomerID=%s", [final_total, cid])
                    cur.execute("""
                        INSERT INTO WalletTransaction (CustomerID, Amount, Type, Description, BookingID)
                        VALUES (%s, %s, 'debit', %s, %s)
                    """, [cid, final_total, f'Payment for Booking #{booking_id}', booking_id])
                    cur.execute("UPDATE Booking SET Status='Confirmed' WHERE BookingID=%s", [booking_id])
                else:
                    mysql.connection.rollback()
                    cur.close()
                    flash('Insufficient wallet balance', 'danger')
                    return redirect(url_for('multi_book', provider_id=provider_id))

            mysql.connection.commit()

            cur.execute("SELECT PersonID FROM Provider WHERE ProviderID=%s", [provider_id])
            pid_row = cur.fetchone()
            if pid_row:
                send_notification(pid_row['PersonID'],
                                  f"New Booking #{booking_id}",
                                  f"Customer booked {len(selected_services)} services. Total: Rs.{final_total}",
                                  booking_id)

            msg = f'Booking created! Total Rs.{final_total:.2f}'
            if discount > 0:
                msg += f' (Saved Rs.{discount:.2f})'
            if pay_with_wallet:
                msg += ' - Paid via Wallet'
            flash(msg, 'success')
            return redirect(url_for('my_bookings'))

        except Exception as e:
            mysql.connection.rollback()
            flash(f'Booking failed: {str(e)}', 'danger')

    cur.execute("""
        SELECT ps.ServiceTypeID, st.ServiceName, sc.CategoryName, ps.PricePerHour, st.Description
        FROM Provider_Service ps
        JOIN Service_Type st ON ps.ServiceTypeID = st.ServiceTypeID
        JOIN Service_Category sc ON st.CategoryID = sc.CategoryID
        WHERE ps.ProviderID = %s
        ORDER BY sc.CategoryName, st.ServiceName
    """, [provider_id])
    services = cur.fetchall()
    cur.close()

    return render_template('multi_book.html',
                           provider=provider,
                           services=services,
                           provider_id=provider_id,
                           wallet_balance=wallet_balance,
                           today=date.today().isoformat())


# ============================================
# AUTH
# ============================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first = request.form['first_name']
        last = request.form['last_name']
        phone = request.form['phone']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        city = request.form.get('city', 'Pune')
        age = request.form.get('age', 0)

        cur = mysql.connection.cursor()
        try:
            cur.execute("SELECT LocationID FROM Location WHERE City=%s", [city])
            loc = cur.fetchone()
            if loc:
                loc_id = loc['LocationID']
            else:
                cur.execute("INSERT INTO Location (City, State) VALUES (%s, 'Maharashtra')", [city])
                loc_id = cur.lastrowid

            cur.execute("""
                INSERT INTO Person (FirstName, LastName, Phone, Age, LocationID)
                VALUES (%s, %s, %s, %s, %s)
            """, [first, last, phone, age, loc_id])
            person_id = cur.lastrowid
            cur.execute("INSERT INTO Person_Email (PersonID, Email, IsPrimary) VALUES (%s, %s, TRUE)",
                        [person_id, email])

            if role == 'customer':
                ref_code = session.pop('referral_code', None)
                referrer_id = None
                if ref_code:
                    cur.execute("SELECT CustomerID FROM Customer WHERE ReferralCode=%s", [ref_code])
                    ref_row = cur.fetchone()
                    if ref_row:
                        referrer_id = ref_row['CustomerID']

                if referrer_id:
                    cur.execute("INSERT INTO Customer (PersonID, ReferredBy) VALUES (%s, %s)",
                                [person_id, referrer_id])
                else:
                    cur.execute("INSERT INTO Customer (PersonID) VALUES (%s)", [person_id])
                customer_id = cur.lastrowid

                my_code = 'PF' + str(customer_id) + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
                cur.execute("UPDATE Customer SET ReferralCode=%s WHERE CustomerID=%s", [my_code, customer_id])

                cur.execute("INSERT INTO Wallet (CustomerID, Balance) VALUES (%s, 500)", [customer_id])
                cur.execute("""
                    INSERT INTO WalletTransaction (CustomerID, Amount, Type, Description)
                    VALUES (%s, 500, 'credit', 'Welcome bonus')
                """, [customer_id])

                if referrer_id:
                    cur.execute("""
                        UPDATE Referral SET RefereeCustomerID=%s, Status='completed', CompletedAt=NOW()
                        WHERE ReferrerCustomerID=%s AND (RefereeEmail IS NULL OR RefereeEmail=%s)
                          AND Status='pending'
                        LIMIT 1
                    """, [customer_id, referrer_id, email])

                    cur.execute("SELECT WalletID FROM Wallet WHERE CustomerID=%s", [referrer_id])
                    if cur.fetchone():
                        cur.execute("UPDATE Wallet SET Balance = Balance + 100 WHERE CustomerID=%s", [referrer_id])
                    else:
                        cur.execute("INSERT INTO Wallet (CustomerID, Balance) VALUES (%s, 100)", [referrer_id])
                    cur.execute("""
                        INSERT INTO WalletTransaction (CustomerID, Amount, Type, Description)
                        VALUES (%s, 100, 'credit', 'Referral reward')
                    """, [referrer_id])

                    cur.execute("UPDATE Wallet SET Balance = Balance + 100 WHERE CustomerID=%s", [customer_id])
                    cur.execute("""
                        INSERT INTO WalletTransaction (CustomerID, Amount, Type, Description)
                        VALUES (%s, 100, 'credit', 'Referral signup bonus')
                    """, [customer_id])

            elif role == 'provider':
                cur.execute("INSERT INTO Provider (PersonID, ExperienceYears, IsVerified) VALUES (%s, 0, FALSE)",
                            [person_id])
                provider_id = cur.lastrowid
                cur.execute("INSERT INTO Individual_Professional (ProviderID) VALUES (%s)", [provider_id])

            pw_hash = generate_password_hash(password)
            cur.execute("""
                INSERT INTO Users (PersonID, Username, PasswordHash, Role)
                VALUES (%s, %s, %s, %s)
            """, [person_id, username, pw_hash, role])

            mysql.connection.commit()
            send_notification(person_id, "Welcome to ProFinder!",
                              f"Hi {first},\n\nWelcome to ProFinder!")
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Registration failed: {str(e)}', 'danger')
        finally:
            cur.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Users WHERE Username = %s", [username])
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user['PasswordHash'], password):
            session['user_id'] = user['UserID']
            session['person_id'] = user['PersonID']
            session['role'] = user['Role']
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('index'))


# ============================================
# DASHBOARD
# ============================================
@app.route('/dashboard')
@login_required
def dashboard():
    role = session['role']
    cur = mysql.connection.cursor()

    if role == 'customer':
        cid = get_customer_id()
        cur.execute("""
            SELECT b.*, st.ServiceName,
                   CONCAT(pp.FirstName,' ',pp.LastName) AS ProviderName,
                   ps.PricePerHour
            FROM Booking b
            JOIN Service_Type st ON b.ServiceTypeID = st.ServiceTypeID
            JOIN Provider p ON b.ProviderID = p.ProviderID
            JOIN Person pp ON p.PersonID = pp.PersonID
            JOIN Provider_Service ps ON p.ProviderID = ps.ProviderID
                 AND st.ServiceTypeID = ps.ServiceTypeID
            WHERE b.CustomerID = %s
            ORDER BY b.BookingDate DESC
        """, [cid])
        bookings = cur.fetchall()
        cur.execute("SELECT COUNT(*) AS c FROM Favorite WHERE CustomerID=%s", [cid])
        fav_count = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM NotificationLog WHERE RecipientPersonID=%s", [session['person_id']])
        notif_count = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM Message WHERE ReceiverID=%s AND IsRead=FALSE", [session['person_id']])
        unread_msgs = cur.fetchone()['c']
        cur.close()
        wallet_balance = get_wallet_balance(cid)
        return render_template('dashboard.html', role=role, bookings=bookings,
                               fav_count=fav_count, notif_count=notif_count,
                               unread_msgs=unread_msgs, wallet_balance=wallet_balance)

    elif role == 'provider':
        pid = get_provider_id()
        cur.execute("""
            SELECT b.*, st.ServiceName,
                   CONCAT(cp.FirstName,' ',cp.LastName) AS CustomerName,
                   cp.Phone AS CustomerPhone,
                   (SELECT Email FROM Person_Email WHERE PersonID = cp.PersonID LIMIT 1) AS CustomerEmail
            FROM Booking b
            JOIN Service_Type st ON b.ServiceTypeID = st.ServiceTypeID
            JOIN Customer c ON b.CustomerID = c.CustomerID
            JOIN Person cp ON c.PersonID = cp.PersonID
            WHERE b.ProviderID = %s
            ORDER BY b.BookingDate DESC
        """, [pid])
        bookings = cur.fetchall()
        cur.execute("SELECT COUNT(*) AS c FROM NotificationLog WHERE RecipientPersonID=%s", [session['person_id']])
        notif_count = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM Message WHERE ReceiverID=%s AND IsRead=FALSE", [session['person_id']])
        unread_msgs = cur.fetchone()['c']
        cur.close()
        return render_template('dashboard.html', role=role, bookings=bookings,
                               notif_count=notif_count, unread_msgs=unread_msgs)

    else:
        cur.execute("SELECT * FROM Provider WHERE IsVerified=FALSE LIMIT 20")
        pending = cur.fetchall()
        cur.execute("SELECT COUNT(*) AS c FROM Booking")
        total_bookings = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM Provider")
        total_providers = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM Customer")
        total_customers = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM Review")
        total_reviews = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM Review WHERE IsApproved=FALSE")
        pending_reviews = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM NotificationLog")
        total_notifs = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM Message")
        total_msgs = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM Coupon")
        total_coupons = cur.fetchone()['c']
        cur.execute("SELECT COUNT(*) AS c FROM Referral WHERE Status='completed'")
        total_refs = cur.fetchone()['c']
        cur.execute("SELECT COALESCE(SUM(Balance),0) AS total FROM Wallet")
        total_wallet = cur.fetchone()['total']
        cur.close()
        return render_template('dashboard.html', role=role, pending=pending,
                               total_bookings=total_bookings,
                               total_providers=total_providers,
                               total_customers=total_customers,
                               total_reviews=total_reviews,
                               pending_reviews=pending_reviews,
                               total_notifs=total_notifs,
                               total_msgs=total_msgs,
                               total_coupons=total_coupons,
                               total_refs=total_refs,
                               total_wallet=total_wallet)


# ============================================
# MY BOOKINGS
# ============================================
@app.route('/my-bookings')
@login_required
def my_bookings():
    if session['role'] != 'customer':
        flash('Only customers have bookings', 'warning')
        return redirect(url_for('dashboard'))
    cid = get_customer_id()
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.BookingID, b.BookingDate, b.BookingTime, b.Status, b.IsEmergency,
               b.CancelledBy, b.TotalPrice, b.DiscountApplied, b.CouponCode, st.ServiceName,
               CONCAT(pp.FirstName,' ',pp.LastName) AS ProviderName,
               pp.Phone AS ProviderPhone, ps.PricePerHour,
               (SELECT COUNT(*) FROM Booking_Service WHERE BookingID=b.BookingID) AS ServiceCount
        FROM Booking b
        JOIN Service_Type st ON b.ServiceTypeID = st.ServiceTypeID
        JOIN Provider p ON b.ProviderID = p.ProviderID
        JOIN Person pp ON p.PersonID = pp.PersonID
        JOIN Provider_Service ps ON p.ProviderID = ps.ProviderID
             AND st.ServiceTypeID = ps.ServiceTypeID
        WHERE b.CustomerID = %s
        ORDER BY b.BookingDate DESC
    """, [cid])
    bookings = cur.fetchall()
    cur.close()
    return render_template('my_bookings.html', bookings=bookings)


@app.route('/booking/<int:bid>')
@login_required
def booking_detail(bid):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.*, st.ServiceName, st.Description AS ServiceDesc,
               CONCAT(pp.FirstName,' ',pp.LastName) AS ProviderName,
               pp.Phone AS ProviderPhone,
               CONCAT(cp.FirstName,' ',cp.LastName) AS CustomerName,
               cp.Phone AS CustomerPhone,
               ps.PricePerHour, p.ProviderID, c.CustomerID
        FROM Booking b
        JOIN Service_Type st ON b.ServiceTypeID = st.ServiceTypeID
        JOIN Provider p ON b.ProviderID = p.ProviderID
        JOIN Person pp ON p.PersonID = pp.PersonID
        JOIN Customer c ON b.CustomerID = c.CustomerID
        JOIN Person cp ON c.PersonID = cp.PersonID
        JOIN Provider_Service ps ON p.ProviderID = ps.ProviderID
             AND st.ServiceTypeID = ps.ServiceTypeID
        WHERE b.BookingID = %s
    """, [bid])
    booking = cur.fetchone()
    if not booking:
        abort(404)

    c = get_customer_id()
    p = get_provider_id()
    is_owner = (c and c == booking['CustomerID']) or (p and p == booking['ProviderID'])
    if not is_owner and session['role'] != 'admin':
        cur.close()
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    cur.execute("""
        SELECT bs.BookingServiceID, st.ServiceName, sc.CategoryName, bs.PricePerHour
        FROM Booking_Service bs
        JOIN Service_Type st ON bs.ServiceTypeID = st.ServiceTypeID
        JOIN Service_Category sc ON st.CategoryID = sc.CategoryID
        WHERE bs.BookingID = %s
    """, [bid])
    extra_services = cur.fetchall()

    cur.execute("SELECT * FROM Review WHERE BookingID=%s", [bid])
    review = cur.fetchone()
    cur.close()
    return render_template('booking_detail.html', booking=booking,
                           extra_services=extra_services, review=review)


@app.route('/booking/<int:bid>/receipt')
@login_required
def booking_receipt(bid):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.*, st.ServiceName, st.Description AS ServiceDesc,
               CONCAT(pp.FirstName,' ',pp.LastName) AS ProviderName,
               pp.Phone AS ProviderPhone,
               CONCAT(cp.FirstName,' ',cp.LastName) AS CustomerName,
               cp.Phone AS CustomerPhone,
               l.City, l.State, ps.PricePerHour
        FROM Booking b
        JOIN Service_Type st ON b.ServiceTypeID = st.ServiceTypeID
        JOIN Provider p ON b.ProviderID = p.ProviderID
        JOIN Person pp ON p.PersonID = pp.PersonID
        JOIN Customer c ON b.CustomerID = c.CustomerID
        JOIN Person cp ON c.PersonID = cp.PersonID
        LEFT JOIN Location l ON pp.LocationID = l.LocationID
        JOIN Provider_Service ps ON p.ProviderID = ps.ProviderID
             AND st.ServiceTypeID = ps.ServiceTypeID
        WHERE b.BookingID = %s
    """, [bid])
    booking = cur.fetchone()
    if not booking:
        abort(404)
    c = get_customer_id()
    p = get_provider_id()
    is_owner = (c and c == booking['CustomerID']) or (p and p == booking['ProviderID'])
    if not is_owner and session['role'] != 'admin':
        cur.close()
        flash('Access denied', 'danger')
        return redirect(url_for('dashboard'))

    cur.execute("""
        SELECT st.ServiceName, bs.PricePerHour
        FROM Booking_Service bs
        JOIN Service_Type st ON bs.ServiceTypeID = st.ServiceTypeID
        WHERE bs.BookingID = %s
    """, [bid])
    all_services = cur.fetchall()
    cur.close()
    return render_template('booking_receipt.html', booking=booking, all_services=all_services)


# ============================================
# PROVIDER MANAGE SERVICES
# ============================================
@app.route('/provider/add-service', methods=['GET', 'POST'])
@login_required
@role_required('provider')
def add_service():
    pid = get_provider_id()
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        service_type_id = request.form['service_type_id']
        price = request.form['price']
        try:
            cur.execute("""
                INSERT INTO Provider_Service (ProviderID, ServiceTypeID, PricePerHour)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE PricePerHour = VALUES(PricePerHour)
            """, [pid, service_type_id, price])
            mysql.connection.commit()
            flash('Service added successfully!', 'success')
            return redirect(url_for('add_service'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')

    cur.execute("""
        SELECT st.ServiceTypeID, st.ServiceName, sc.CategoryName
        FROM Service_Type st
        JOIN Service_Category sc ON st.CategoryID = sc.CategoryID
        WHERE st.ServiceTypeID NOT IN (
            SELECT ServiceTypeID FROM Provider_Service WHERE ProviderID = %s
        )
        ORDER BY sc.CategoryName, st.ServiceName
    """, [pid])
    available_services = cur.fetchall()
    cur.execute("""
        SELECT ps.ProviderServiceID, st.ServiceName, sc.CategoryName, ps.PricePerHour
        FROM Provider_Service ps
        JOIN Service_Type st ON ps.ServiceTypeID = st.ServiceTypeID
        JOIN Service_Category sc ON st.CategoryID = sc.CategoryID
        WHERE ps.ProviderID = %s
        ORDER BY sc.CategoryName
    """, [pid])
    my_services = cur.fetchall()
    cur.close()
    return render_template('add_service.html',
                           available_services=available_services,
                           my_services=my_services)


@app.route('/provider/remove-service/<int:psid>')
@login_required
@role_required('provider')
def remove_service(psid):
    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            DELETE ps FROM Provider_Service ps
            JOIN Provider p ON ps.ProviderID = p.ProviderID
            WHERE ps.ProviderServiceID = %s AND p.PersonID = %s
        """, [psid, session['person_id']])
        mysql.connection.commit()
        flash('Service removed!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'Error: {str(e)}', 'danger')
    cur.close()
    return redirect(url_for('add_service'))


# ============================================
# SINGLE BOOKING
# ============================================
@app.route('/book/<int:provider_id>/<int:service_id>', methods=['GET', 'POST'])
@login_required
def book_service(provider_id, service_id):
    if session['role'] != 'customer':
        flash('Only customers can book', 'warning')
        return redirect(url_for('index'))
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        date_val = request.form['date']
        time_val = request.form['time']
        emergency = 'emergency' in request.form
        try:
            datetime.strptime(date_val, '%Y-%m-%d')
            datetime.strptime(time_val, '%H:%M')
        except ValueError:
            flash('Invalid date or time', 'danger')
            return redirect(url_for('book_service', provider_id=provider_id, service_id=service_id))
        cid = get_customer_id()
        try:
            cur.execute("""
                INSERT INTO Booking (CustomerID, ProviderID, ServiceTypeID, BookingDate, BookingTime, IsEmergency)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, [cid, provider_id, service_id, date_val, time_val, emergency])
            booking_id = cur.lastrowid
            cur.execute("SELECT PricePerHour FROM Provider_Service WHERE ProviderID=%s AND ServiceTypeID=%s",
                        [provider_id, service_id])
            pr = cur.fetchone()
            price = float(pr['PricePerHour']) if pr else 500
            cur.execute("""
                INSERT INTO Booking_Service (BookingID, ServiceTypeID, PricePerHour)
                VALUES (%s, %s, %s)
            """, [booking_id, service_id, price])
            cur.execute("UPDATE Booking SET TotalPrice=%s WHERE BookingID=%s", [price, booking_id])
            mysql.connection.commit()
            cur.execute("SELECT PersonID FROM Provider WHERE ProviderID=%s", [provider_id])
            pid_row = cur.fetchone()
            if pid_row:
                send_notification(pid_row['PersonID'], f"New Booking #{booking_id}",
                                  f"New booking on {date_val} at {time_val}.", booking_id)
            flash('Booking created!', 'success')
            return redirect(url_for('my_bookings'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Booking failed: {str(e)}', 'danger')

    cur.execute("""
        SELECT st.*, ps.PricePerHour, sc.CategoryName
        FROM Service_Type st
        JOIN Provider_Service ps ON st.ServiceTypeID = ps.ServiceTypeID
        JOIN Service_Category sc ON st.CategoryID = sc.CategoryID
        WHERE ps.ProviderID=%s AND st.ServiceTypeID=%s
    """, [provider_id, service_id])
    service = cur.fetchone()
    cur.close()
    return render_template('booking.html', service=service,
                           provider_id=provider_id, today=date.today().isoformat())


@app.route('/booking/<int:bid>/cancel', methods=['POST'])
@login_required
def cancel_booking(bid):
    cur = mysql.connection.cursor()
    cid = get_customer_id()
    if not cid:
        flash('Only customers can cancel', 'danger')
        return redirect(url_for('dashboard'))
    cur.execute("SELECT Status, ProviderID, TotalPrice FROM Booking WHERE BookingID=%s AND CustomerID=%s", [bid, cid])
    row = cur.fetchone()
    if not row:
        cur.close()
        flash('Booking not found', 'danger')
        return redirect(url_for('my_bookings'))
    if row['Status'] not in ('Pending', 'Confirmed'):
        cur.close()
        flash('Cannot cancel', 'warning')
        return redirect(url_for('my_bookings'))
    cur.execute("UPDATE Booking SET Status='Cancelled', CancelledBy='customer' WHERE BookingID=%s", [bid])

    cur.execute("""
        SELECT * FROM WalletTransaction
        WHERE BookingID=%s AND Type='debit'
    """, [bid])
    debit = cur.fetchone()
    if debit:
        refund = float(debit['Amount'])
        cur.execute("UPDATE Wallet SET Balance = Balance + %s WHERE CustomerID=%s", [refund, cid])
        cur.execute("""
            INSERT INTO WalletTransaction (CustomerID, Amount, Type, Description, BookingID)
            VALUES (%s, %s, 'credit', %s, %s)
        """, [cid, refund, f'Refund for cancelled Booking #{bid}', bid])

    cur.execute("SELECT PersonID FROM Provider WHERE ProviderID=%s", [row['ProviderID']])
    pid_row = cur.fetchone()
    if pid_row:
        send_notification(pid_row['PersonID'], f"Booking #{bid} Cancelled",
                          f"The customer cancelled booking #{bid}.", bid)
    mysql.connection.commit()
    cur.close()
    flash('Booking cancelled', 'info')
    return redirect(url_for('my_bookings'))


@app.route('/booking/<int:bid>/accept')
@login_required
def accept_booking(bid):
    if session['role'] != 'provider':
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.CustomerID, b.BookingDate, b.BookingTime, c.PersonID AS CustomerPersonID
        FROM Booking b JOIN Customer c ON b.CustomerID = c.CustomerID WHERE b.BookingID=%s
    """, [bid])
    row = cur.fetchone()
    cur.execute("UPDATE Booking SET Status='Confirmed' WHERE BookingID=%s", [bid])
    if row:
        send_notification(row['CustomerPersonID'], f"Booking #{bid} Confirmed",
                          f"Your booking on {row['BookingDate']} at {row['BookingTime']} is confirmed!", bid)
    mysql.connection.commit()
    cur.close()
    flash('Booking accepted!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/booking/<int:bid>/reject')
@login_required
def reject_booking(bid):
    if session['role'] != 'provider':
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.PersonID AS CustomerPersonID
        FROM Booking b JOIN Customer c ON b.CustomerID = c.CustomerID WHERE b.BookingID=%s
    """, [bid])
    row = cur.fetchone()
    cur.execute("UPDATE Booking SET Status='Cancelled', CancelledBy='provider' WHERE BookingID=%s", [bid])
    if row:
        send_notification(row['CustomerPersonID'], f"Booking #{bid} Declined",
                          f"Booking #{bid} was declined.", bid)
    mysql.connection.commit()
    cur.close()
    flash('Booking rejected', 'info')
    return redirect(url_for('dashboard'))


@app.route('/booking/<int:bid>/complete')
@login_required
def complete_booking(bid):
    if session['role'] != 'provider':
        flash('Unauthorized', 'danger')
        return redirect(url_for('dashboard'))
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.PersonID AS CustomerPersonID
        FROM Booking b JOIN Customer c ON b.CustomerID = c.CustomerID WHERE b.BookingID=%s
    """, [bid])
    row = cur.fetchone()
    cur.execute("UPDATE Booking SET Status='Completed' WHERE BookingID=%s", [bid])
    if row:
        send_notification(row['CustomerPersonID'], f"Booking #{bid} Completed",
                          f"Your booking #{bid} is complete!", bid)
    mysql.connection.commit()
    cur.close()
    flash('Booking marked Completed!', 'success')
    return redirect(url_for('dashboard'))


# ============================================
# REVIEWS
# ============================================
@app.route('/review/<int:booking_id>', methods=['POST'])
@login_required
def submit_review(booking_id):
    if session['role'] != 'customer':
        return redirect(url_for('dashboard'))
    try:
        rating = int(request.form['rating'])
        if rating < 1 or rating > 5:
            raise ValueError
    except (ValueError, KeyError):
        flash('Rating 1-5 only', 'danger')
        return redirect(url_for('my_bookings'))
    comment = request.form.get('comment', '').strip()
    if not comment:
        flash('Please write a review', 'danger')
        return redirect(url_for('my_bookings'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.ProviderID, c.CustomerID, pp.PersonID AS ProviderPersonID
        FROM Booking b
        JOIN Customer c ON b.CustomerID = c.CustomerID
        JOIN Provider pr ON b.ProviderID = pr.ProviderID
        JOIN Person pp ON pr.PersonID = pp.PersonID
        WHERE b.BookingID=%s AND c.PersonID=%s AND b.Status='Completed'
    """, [booking_id, session['person_id']])
    row = cur.fetchone()
    if row:
        try:
            cur.execute("""
                INSERT INTO Review (BookingID, CustomerID, ProviderID, Comment, Rating, IsApproved)
                VALUES (%s, %s, %s, %s, %s, TRUE)
            """, [booking_id, row['CustomerID'], row['ProviderID'], comment, rating])
            cur.execute("""
                UPDATE Provider SET AvgRating = (
                    SELECT ROUND(AVG(Rating),2) FROM Review WHERE ProviderID = %s AND IsApproved = TRUE
                ) WHERE ProviderID = %s
            """, [row['ProviderID'], row['ProviderID']])
            mysql.connection.commit()
            send_notification(row['ProviderPersonID'], f"New Review for Booking #{booking_id}",
                              f"You received a {rating}-star review.", booking_id)
            flash('Review submitted!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
    cur.close()
    return redirect(url_for('my_bookings'))


# ============================================
# ADMIN
# ============================================
@app.route('/admin/verify/<int:provider_id>')
@login_required
@role_required('admin')
def verify_provider(provider_id):
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Provider SET IsVerified=TRUE WHERE ProviderID=%s", [provider_id])
    mysql.connection.commit()
    cur.close()
    flash('Provider verified!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/admin/reviews')
@login_required
@role_required('admin')
def admin_reviews():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT r.*, CONCAT(cp.FirstName,' ',cp.LastName) AS CustomerName,
               CONCAT(pp.FirstName,' ',pp.LastName) AS ProviderName
        FROM Review r
        JOIN Customer c ON r.CustomerID = c.CustomerID
        JOIN Person cp ON c.PersonID = cp.PersonID
        JOIN Provider p ON r.ProviderID = p.ProviderID
        JOIN Person pp ON p.PersonID = pp.PersonID
        ORDER BY r.IsApproved ASC, r.ReviewDate DESC LIMIT 100
    """)
    reviews = cur.fetchall()
    cur.close()
    return render_template('admin_reviews.html', reviews=reviews)


@app.route('/admin/review/<int:rid>/toggle')
@login_required
@role_required('admin')
def toggle_review(rid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT ProviderID, IsApproved FROM Review WHERE ReviewID=%s", [rid])
    row = cur.fetchone()
    if not row:
        cur.close()
        flash('Review not found', 'danger')
        return redirect(url_for('admin_reviews'))
    new_val = not row['IsApproved']
    cur.execute("UPDATE Review SET IsApproved=%s WHERE ReviewID=%s", [new_val, rid])
    cur.execute("""
        UPDATE Provider SET AvgRating = COALESCE((
            SELECT ROUND(AVG(Rating),2) FROM Review WHERE ProviderID = %s AND IsApproved = TRUE
        ), 0) WHERE ProviderID = %s
    """, [row['ProviderID'], row['ProviderID']])
    mysql.connection.commit()
    cur.close()
    flash(f"Review {'approved' if new_val else 'hidden'}", 'success')
    return redirect(url_for('admin_reviews'))


@app.route('/admin/referrals')
@login_required
@role_required('admin')
def admin_referrals():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT r.*,
               CONCAT(rp.FirstName,' ',rp.LastName) AS ReferrerName,
               CONCAT(fp.FirstName,' ',fp.LastName) AS RefereeName
        FROM Referral r
        JOIN Customer rc ON r.ReferrerCustomerID = rc.CustomerID
        JOIN Person rp ON rc.PersonID = rp.PersonID
        LEFT JOIN Customer fc ON r.RefereeCustomerID = fc.CustomerID
        LEFT JOIN Person fp ON fc.PersonID = fp.PersonID
        ORDER BY r.CreatedAt DESC
        LIMIT 100
    """)
    referrals = cur.fetchall()

    cur.execute("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN Status='completed' THEN 1 ELSE 0 END) AS completed,
               COALESCE(SUM(CASE WHEN Status='completed' THEN RewardAmount ELSE 0 END), 0) AS paid
        FROM Referral
    """)
    stats = cur.fetchone()
    cur.close()
    return render_template('admin_referrals.html', referrals=referrals, stats=stats)


# ============================================
# UTILITY
# ============================================
@app.route('/setup-passwords')
def setup_passwords():
    cur = mysql.connection.cursor()
    h = generate_password_hash('password123')
    cur.execute("UPDATE Users SET PasswordHash=%s", [h])
    mysql.connection.commit()
    cur.execute("SELECT COUNT(*) AS c FROM Users")
    total = cur.fetchone()['c']
    cur.close()
    return f"<h2>Passwords reset for {total} users. All use 'password123'</h2><a href='/login'>Go to Login</a>"


@app.route('/test-db')
def test_db():
    try:
        cur = mysql.connection.cursor()
        stats = {}
        for table in ['Person', 'Provider', 'Customer', 'Booking', 'Review',
                      'Service_Type', 'Location', 'Favorite', 'NotificationLog',
                      'Message', 'Booking_Service', 'Coupon', 'Booking_Coupon',
                      'Wallet', 'WalletTransaction', 'Referral']:
            cur.execute(f"SELECT COUNT(*) AS c FROM {table}")
            stats[table] = cur.fetchone()['c']
        cur.close()
        html = "<h2>Database Connected</h2><ul>"
        for k, v in stats.items():
            html += f"<li>{k}: {v}</li>"
        html += "</ul><a href='/'>Back</a>"
        return html
    except Exception as e:
        return f"<h2>Error</h2><pre>{str(e)}</pre>", 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)