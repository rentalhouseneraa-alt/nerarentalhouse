from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, send_file, make_response
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash
from app import db
from app.models import User, Customer, Order
from app.forms import LoginForm, CreateStaffForm, CustomerOrderForm
from app.utils import save_upload, parse_datetime_str
import os, io, csv, json, zipfile
from datetime import datetime, timedelta
try:
    from xhtml2pdf import pisa
    XHTML2PDF_AVAILABLE = True
except Exception:
    XHTML2PDF_AVAILABLE = False

bp = Blueprint('main', __name__)

# --- Auth ---
@bp.route('/', methods=['GET', 'POST'])
def auth_login():
    if current_user.is_authenticated:
        return redirect(url_for('main.admin_dashboard') if current_user.is_admin else url_for('main.staff_dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Logged in successfully', 'success')
            return redirect(url_for('main.admin_dashboard') if user.is_admin else url_for('main.staff_dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html', form=form)

@bp.route('/logout')
@login_required
def auth_logout():
    logout_user()
    flash('Logged out', 'info')
    return redirect(url_for('main.auth_login'))

# --- Admin ---
@bp.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('main.staff_dashboard'))

    total_orders = Order.query.count()
    pending = Order.query.filter_by(status='pending').count()
    approved = Order.query.filter_by(status='approved').count()
    completed = Order.query.filter_by(status='completed').count()
    canceled = Order.query.filter_by(status='canceled').count()

    completed_orders = Order.query.filter_by(status='completed').all()
    total_revenue = sum([o.total_amount or 0.0 for o in completed_orders])

    staff_perf = []
    users = User.query.all()
    for u in users:
        cnt = Order.query.filter_by(staff_id=u.id).count()
        approved_cnt = Order.query.filter_by(staff_id=u.id, status='approved').count()
        revenue = sum([o.total_amount or 0 for o in Order.query.filter_by(staff_id=u.id, status='completed').all()])
        staff_perf.append({'staff': u, 'orders': cnt, 'approved': approved_cnt, 'revenue': revenue})

    staff_perf = sorted(staff_perf, key=lambda x: x['orders'], reverse=True)

    return render_template('admin/dashboard.html',
                           total_orders=total_orders,
                           pending=pending,
                           approved=approved,
                           completed=completed,
                           canceled=canceled,
                           total_revenue=total_revenue,
                           staff_perf=staff_perf,
                           xhtml2pdf=XHTML2PDF_AVAILABLE)

@bp.route('/admin/staffs', methods=['GET', 'POST'])
@login_required
def admin_staffs():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('main.staff_dashboard'))
    form = CreateStaffForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists', 'danger')
        else:
            user = User(username=form.username.data, full_name=form.full_name.data, email=None, is_admin=form.is_admin.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Staff created', 'success')
            return redirect(url_for('main.admin_staffs'))
    staffs = User.query.all()
    return render_template('admin/staffs.html', form=form, staffs=staffs)

@bp.route('/admin/orders')
@login_required
def admin_orders():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('main.staff_dashboard'))

    q = request.args.get('q', '').strip()
    if q:
        orders = Order.query.join(Order.customer).join(Order.staff).filter(
            (Customer.name.ilike(f"%{q}%")) |
            (Order.product_name.ilike(f"%{q}%")) |
            (User.full_name.ilike(f"%{q}%")) |
            (Order.created_at.cast(db.String).ilike(f"%{q}%"))
        ).order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.order_by(Order.created_at.desc()).all()

    return render_template('admin/orders.html', orders=orders)

@bp.route('/admin/order/<int:order_id>/view')
@login_required
def admin_view_order(order_id):
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('main.staff_dashboard'))
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_view.html', order=order)


@bp.route('/admin/order/<int:order_id>/approve')
@login_required
def admin_approve(order_id):
    if not current_user.is_admin:
        flash('Access denied', 'danger'); return redirect(url_for('main.staff_dashboard'))
    order = Order.query.get_or_404(order_id)
    order.status = 'approved'
    order.amount_pending = (order.total_amount or (order.price * order.quantity)) - (order.amount_advance or 0)
    db.session.commit()
    flash('Order approved', 'success')
    return redirect(url_for('main.admin_orders'))


@bp.route('/admin/order/<int:order_id>/reject')
@login_required
def admin_reject(order_id):
    if not current_user.is_admin:
        flash('Access denied', 'danger'); return redirect(url_for('main.staff_dashboard'))
    order = Order.query.get_or_404(order_id)
    order.status = 'rejected'
    db.session.commit()
    flash('Order rejected', 'warning')
    return redirect(url_for('main.admin_orders'))


@bp.route('/admin/order/<int:order_id>/complete')
@login_required
def admin_complete(order_id):
    if not current_user.is_admin:
        flash('Access denied', 'danger'); return redirect(url_for('main.staff_dashboard'))
    order = Order.query.get_or_404(order_id)
    order.status = 'completed'
    db.session.commit()
    flash('Order marked as completed', 'success')
    return redirect(url_for('main.admin_orders'))


@bp.route('/admin/order/<int:order_id>/cancel', methods=['POST'])
@login_required
def admin_cancel(order_id):
    if not current_user.is_admin:
        flash('Access denied', 'danger'); return redirect(url_for('main.staff_dashboard'))
    order = Order.query.get_or_404(order_id)
    order.status = 'canceled'
    db.session.commit()
    flash('Order canceled (kept in records)', 'warning')
    return redirect(url_for('main.admin_orders'))


@bp.route('/admin/order/<int:order_id>/edit', methods=['GET','POST'])
@login_required
def admin_edit_order(order_id):
    """
    Edit page:
     - show customer details, staff details, product images
     - allow admin to change fields and change status (pending/approved/completed/canceled)
    """
    if not current_user.is_admin:
        flash('Access denied', 'danger'); return redirect(url_for('main.staff_dashboard'))
    order = Order.query.get_or_404(order_id)
    form = CustomerOrderForm()
    if request.method == 'GET':
        # populate form fields from order
        if order.customer:
            form.customer_name.data = order.customer.name
            form.phone.data = order.customer.phone
            form.address.data = order.customer.address
        form.product_name.data = order.product_name
        form.product_details.data = order.product_details
        form.price.data = order.price
        form.quantity.data = order.quantity
        form.delivery_datetime.data = order.delivery_datetime.strftime('%Y-%m-%d %H:%M') if order.delivery_datetime else ''
        form.return_datetime.data = order.return_datetime.strftime('%Y-%m-%d %H:%M') if order.return_datetime else ''
        form.amount_advance.data = order.amount_advance
    if form.validate_on_submit():
        # allow admin to change status via form field 'status'
        new_status = request.form.get('status')
        if new_status:
            order.status = new_status

        # update customer
        if not order.customer:
            customer = Customer(name=form.customer_name.data, phone=form.phone.data, address=form.address.data)
            db.session.add(customer)
            db.session.flush()
            order.customer_id = customer.id
        else:
            order.customer.name = form.customer_name.data
            order.customer.phone = form.phone.data
            order.customer.address = form.address.data

        # update order details
        order.product_name = form.product_name.data
        order.product_details = form.product_details.data
        order.price = form.price.data
        order.quantity = form.quantity.data
        order.delivery_datetime = parse_datetime_str(form.delivery_datetime.data)
        order.return_datetime = parse_datetime_str(form.return_datetime.data)
        order.amount_advance = form.amount_advance.data or 0.0

        order.total_amount = (order.price or 0.0) * (order.quantity or 1)
        order.amount_pending = (order.total_amount or 0.0) - (order.amount_advance or 0.0)

        # handle uploaded photos appended to existing list
        files = request.files.getlist('photos')
        filenames = order.get_photos()
        for f in files:
            saved = save_upload(f)
            if saved:
                filenames.append(saved)
        order.set_photos(filenames)

        db.session.commit()
        flash('Order edited', 'success')
        return redirect(url_for('main.admin_orders'))
    return render_template('admin/order_edit.html', form=form, order=order)


@bp.route('/admin/order/<int:order_id>/bill')
@login_required
def admin_bill(order_id):
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('main.staff_dashboard'))

    order = Order.query.get_or_404(order_id)
    company_name = "Neraa Rental House"  # You can change this

    if request.args.get('format') == 'pdf' and XHTML2PDF_AVAILABLE:
        html = render_template('admin/bill.html', order=order, company_name=company_name, pdf=True)
        pdf = io.BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf)
        if pisa_status.err:
            flash('Error generating PDF', 'danger')
            return render_template('admin/bill.html', order=order, company_name=company_name)
        pdf.seek(0)
        return send_file(pdf, mimetype='application/pdf',
                         download_name=f"bill_order_{order.id}.pdf", as_attachment=True)

    return render_template('admin/bill.html', order=order, company_name=company_name, pdf=False)


@bp.route('/admin/reports')
@login_required
def admin_reports():
    if not current_user.is_admin:
        flash('Access denied', 'danger'); return redirect(url_for('main.staff_dashboard'))
    return render_template('admin/reports.html', xhtml2pdf=XHTML2PDF_AVAILABLE)


@bp.route('/admin/reports/download', methods=['GET'])
@login_required
def admin_reports_download():
    if not current_user.is_admin:
        flash('Access denied', 'danger'); return redirect(url_for('main.staff_dashboard'))

    typ = request.args.get('type', 'daily')
    date = request.args.get('date')
    rows = []
    if typ == 'daily' and date:
        day = datetime.strptime(date, '%Y-%m-%d').date()
        start = datetime.combine(day, datetime.min.time())
        end = start + timedelta(days=1)
    elif typ == 'monthly' and date:
        dt = datetime.strptime(date, '%Y-%m')
        start = dt
        if dt.month == 12:
            end = datetime(dt.year+1, 1, 1)
        else:
            end = datetime(dt.year, dt.month+1, 1)
    else:
        flash('Invalid parameters', 'danger'); return redirect(url_for('main.admin_reports'))

    orders = Order.query.filter(Order.created_at >= start, Order.created_at < end).order_by(Order.created_at.asc()).all()

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Order ID','Created','Staff','Customer','Phone','Product','Price','Quantity','Total','Advance','Pending','Status','Delivery','Return'])
    for o in orders:
        cw.writerow([
            o.id,
            o.created_at.strftime('%Y-%m-%d %H:%M'),
            o.staff.username if o.staff else '',
            o.customer.name if o.customer else '',
            o.customer.phone if o.customer else '',
            o.product_name,
            f"{o.price:.2f}",
            o.quantity,
            f"{o.total_amount:.2f}" if o.total_amount else f"{(o.price*o.quantity):.2f}",
            f"{o.amount_advance:.2f}",
            f"{o.amount_pending:.2f}",
            o.status,
            o.delivery_datetime.strftime('%Y-%m-%d %H:%M') if o.delivery_datetime else '',
            o.return_datetime.strftime('%Y-%m-%d %H:%M') if o.return_datetime else ''
        ])
    output = make_response(si.getvalue())
    filename = f"{typ}_report_{date}.csv"
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    output.headers["Content-type"] = "text/csv"
    return output


@bp.route('/admin/reports/download_bills', methods=['GET'])
@login_required
def admin_download_bills():
    """
    Generate a ZIP of bill PDFs for orders within a day or month.
    Query args:
      type = 'daily' or 'monthly'
      date = 'YYYY-MM-DD' or 'YYYY-MM'
    """
    if not current_user.is_admin:
        flash('Access denied', 'danger'); return redirect(url_for('main.staff_dashboard'))

    if not XHTML2PDF_AVAILABLE:
        flash('PDF library not available on server', 'danger')
        return redirect(url_for('main.admin_reports'))

    typ = request.args.get('type', 'daily')
    date = request.args.get('date')
    if typ == 'daily' and date:
        day = datetime.strptime(date, '%Y-%m-%d').date()
        start = datetime.combine(day, datetime.min.time())
        end = start + timedelta(days=1)
    elif typ == 'monthly' and date:
        dt = datetime.strptime(date, '%Y-%m')
        start = dt
        if dt.month == 12:
            end = datetime(dt.year+1, 1, 1)
        else:
            end = datetime(dt.year, dt.month+1, 1)
    else:
        flash('Invalid parameters', 'danger'); return redirect(url_for('main.admin_reports'))

    orders = Order.query.filter(Order.created_at >= start, Order.created_at < end).order_by(Order.created_at.asc()).all()
    if not orders:
        flash('No orders found for selected range', 'info')
        return redirect(url_for('main.admin_reports'))

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for o in orders:
            html = render_template('admin/bill.html', order=o)
            pdf_io = io.BytesIO()
            pisa_status = pisa.CreatePDF(io.StringIO(html), dest=pdf_io)
            if pisa_status.err:
                continue
            pdf_io.seek(0)
            zipf.writestr(f"bill_order_{o.id}.pdf", pdf_io.read())
    zip_buffer.seek(0)
    name = f"bills_{typ}_{date}.zip"
    return send_file(zip_buffer, mimetype='application/zip', download_name=name, as_attachment=True)

# --- Staff ---
@bp.route('/staff')
@login_required
def staff_dashboard():
    if current_user.is_admin:
        return redirect(url_for('main.admin_dashboard'))
    my_orders = Order.query.filter_by(staff_id=current_user.id).all()
    total = len(my_orders)
    pending = len([o for o in my_orders if o.status == 'pending'])
    approved = len([o for o in my_orders if o.status == 'approved'])
    completed = len([o for o in my_orders if o.status == 'completed'])
    revenue = sum([o.total_amount or (o.price*o.quantity) for o in my_orders if o.status == 'completed'])
    return render_template('staff/dashboard.html', total=total, pending=pending, approved=approved, completed=completed, revenue=revenue)

@bp.route('/staff/orders')
@login_required
def staff_orders():
    if current_user.is_admin:
        return redirect(url_for('main.admin_orders'))
    orders = Order.query.filter_by(staff_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('staff/orders.html', orders=orders)

@bp.route('/staff/order/<int:order_id>/view')
@login_required
def staff_view_order(order_id):
    order = Order.query.get_or_404(order_id)
    if current_user.id != order.staff_id:
        flash('Access denied', 'danger'); return redirect(url_for('main.staff_orders'))
    return render_template('staff/order_view.html', order=order)

@bp.route('/staff/new', methods=['GET','POST'])
@login_required
def staff_new_customer():
    if current_user.is_admin:
        flash('Access denied for admin on staff page', 'danger'); return redirect(url_for('main.admin_dashboard'))
    form = CustomerOrderForm()
    if form.validate_on_submit():
        customer = Customer.query.filter_by(phone=form.phone.data).first()
        if not customer:
            customer = Customer(name=form.customer_name.data, phone=form.phone.data, address=form.address.data)
            db.session.add(customer)
            db.session.commit()
        order = Order(
            product_name=form.product_name.data,
            product_details=form.product_details.data,
            price=form.price.data,
            quantity=form.quantity.data,
            delivery_datetime=parse_datetime_str(form.delivery_datetime.data),
            return_datetime=parse_datetime_str(form.return_datetime.data),
            amount_advance=form.amount_advance.data or 0.0,
            staff_id=current_user.id,
            customer_id=customer.id,
            status='pending'
        )
        order.total_amount = (form.price.data or 0.0) * (form.quantity.data or 1)
        order.amount_pending = order.total_amount - (order.amount_advance or 0.0)

        filenames = []
        files = request.files.getlist('photos')
        for f in files:
            saved = save_upload(f)
            if saved:
                filenames.append(saved)
        order.set_photos(filenames)

        db.session.add(order)
        db.session.commit()
        flash('Order saved and pending admin approval', 'success')
        return redirect(url_for('main.staff_orders'))
    return render_template('staff/new_customer.html', form=form)

@bp.route('/staff/order/<int:order_id>/edit', methods=['GET','POST'])
@login_required
def staff_edit_order(order_id):
    # keep this but restrict: staff can edit their own orders only if not approved
    order = Order.query.get_or_404(order_id)
    if current_user.id != order.staff_id:
        flash('Access denied', 'danger'); return redirect(url_for('main.staff_orders'))
    if order.status == 'approved':
        flash('Cannot edit approved order', 'warning'); return redirect(url_for('main.staff_orders'))

    form = CustomerOrderForm()
    if request.method == 'GET':
        form.customer_name.data = order.customer.name
        form.phone.data = order.customer.phone
        form.address.data = order.customer.address
        form.product_name.data = order.product_name
        form.product_details.data = order.product_details
        form.price.data = order.price
        form.quantity.data = order.quantity
        form.delivery_datetime.data = order.delivery_datetime.strftime('%Y-%m-%d %H:%M') if order.delivery_datetime else ''
        form.return_datetime.data = order.return_datetime.strftime('%Y-%m-%d %H:%M') if order.return_datetime else ''
        form.amount_advance.data = order.amount_advance
    if form.validate_on_submit():
        order.customer.name = form.customer_name.data
        order.customer.phone = form.phone.data
        order.customer.address = form.address.data
        order.product_name = form.product_name.data
        order.product_details = form.product_details.data
        order.price = form.price.data
        order.quantity = form.quantity.data
        order.delivery_datetime = parse_datetime_str(form.delivery_datetime.data)
        order.return_datetime = parse_datetime_str(form.return_datetime.data)
        order.amount_advance = form.amount_advance.data or 0.0
        order.total_amount = order.price * order.quantity
        order.amount_pending = order.total_amount - order.amount_advance

        files = request.files.getlist('photos')
        filenames = order.get_photos()
        for f in files:
            saved = save_upload(f)
            if saved:
                filenames.append(saved)
        order.set_photos(filenames)

        # after edit, set to pending for admin approval again
        order.status = 'pending'
        db.session.commit()
        flash('Order updated and sent for admin approval', 'success')
        return redirect(url_for('main.staff_orders'))
    return render_template('staff/new_customer.html', form=form, order=order)

@bp.route('/uploads/<filename>')
def uploaded_file(filename):
    # serve uploaded files
    return send_file(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
