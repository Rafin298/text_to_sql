from django.core.management.base import BaseCommand
from django.conf import settings
import pandas as pd
import os
import time
import datetime
from data_loader import models

def parse_date_safe(val):
    if pd.isna(val):
        return None
    try:
        return pd.to_datetime(val, errors='coerce')
    except Exception:
        return None

class CSVLoader:
    """
    Encapsulates the CSV normalization pipeline.
    Usage:
        loader = CSVLoader(csv_root="/path/to/csvs", create_missing_parents=False)
        report = loader.run()
    """

    DEFAULT_FILENAMES = {
        'categories': 'categories.csv',
        'customers': 'customers.csv',
        'employees': 'employees.csv',
        'order_details': 'order_details.csv',
        'orders': 'orders.csv',
        'products': 'products.csv',
        'shippers': 'shippers.csv',
    }

    def __init__(self, csv_root=None, create_missing_parents=False):
        self.csv_root = csv_root or getattr(settings, 'CSV_ROOT', None)
        if not self.csv_root:
            raise ValueError("csv_root must be provided either in settings.CSV_ROOT or to CSVLoader")
        self.create_missing_parents = create_missing_parents
        self.metrics = {
            'started_at': datetime.datetime.now(datetime.timezone.utc),
            'processed': {},
            'inserted': {},
            'errors': {},
            'referential_violations': {},
            'null_counts': {},
        }

    def _load_df(self, filename, **kwargs):
        path = os.path.join(self.csv_root, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV not found: {path}")
        df = pd.read_csv(path, dtype=str, encoding="ISO-8859-1",keep_default_na=False, na_values=['', 'NULL', 'NaN'])
        return df

    def _count_nulls(self, df):
        # count empty/NA cells
        return int(df.isnull().sum().sum())

    def run(self):
        start = time.time()
        report = self.metrics
        try:
            # load files (order matters: parents first)
            categories_df = self._load_df(self.DEFAULT_FILENAMES['categories'])
            report['processed']['categories'] = len(categories_df)
            report['null_counts']['categories'] = self._count_nulls(categories_df)

            customers_df = self._load_df(self.DEFAULT_FILENAMES['customers'])
            report['processed']['customers'] = len(customers_df)
            report['null_counts']['customers'] = self._count_nulls(customers_df)

            employees_df = self._load_df(self.DEFAULT_FILENAMES['employees'])
            report['processed']['employees'] = len(employees_df)
            report['null_counts']['employees'] = self._count_nulls(employees_df)

            shippers_df = self._load_df(self.DEFAULT_FILENAMES['shippers'])
            report['processed']['shippers'] = len(shippers_df)
            report['null_counts']['shippers'] = self._count_nulls(shippers_df)

            products_df = self._load_df(self.DEFAULT_FILENAMES['products'])
            report['processed']['products'] = len(products_df)
            report['null_counts']['products'] = self._count_nulls(products_df)

            orders_df = self._load_df(self.DEFAULT_FILENAMES['orders'])
            report['processed']['orders'] = len(orders_df)
            report['null_counts']['orders'] = self._count_nulls(orders_df)

            order_details_df = self._load_df(self.DEFAULT_FILENAMES['order_details'])
            report['processed']['order_details'] = len(order_details_df)
            report['null_counts']['order_details'] = self._count_nulls(order_details_df)

            # validate & insert in DB using transactions and bulk ops
            self._insert_categories(categories_df, report)
            self._insert_customers(customers_df, report)
            self._insert_employees(employees_df, report)
            self._insert_shippers(shippers_df, report)
            self._insert_products(products_df, report)
            self._insert_orders(orders_df, report)
            self._insert_order_details(order_details_df, report)

        except Exception as e:
            # catch-all: record error and re-raise
            report['errors']['fatal'] = str(e)
            raise
        finally:
            end = time.time()
            report['finished_at'] = datetime.datetime.utcnow()
            report['duration_seconds'] = end - start
        return report

    # Insert helpers: each does validation and uses bulk_create
    def _insert_categories(self, df, report):
        created = 0
        errors = 0
        objs = []
        for _, row in df.iterrows():
            try:
                cat_id = int(row.get('categoryID')) if row.get('categoryID') else None
                if cat_id is None:
                    errors += 1
                    continue
                objs.append(models.Category(categoryID=cat_id,
                                           categoryName=row.get('categoryName') or '',
                                           description=row.get('description') or None))
            except Exception:
                errors += 1
        if objs:
            models.Category.objects.bulk_create(objs, ignore_conflicts=True)
            created = len(objs)
        report['inserted']['categories'] = created
        report['errors']['categories'] = errors

    def _insert_customers(self, df, report):
        created = 0
        errors = 0
        objs = []
        for _, row in df.iterrows():
            try:
                cid = row.get('customerID')
                if not cid:
                    errors += 1; continue
                objs.append(models.Customer(
                    customerID=cid,
                    companyName=row.get('companyName') or '',
                    contactName=row.get('contactName') or None,
                    contactTitle=row.get('contactTitle') or None,
                    city=row.get('city') or None,
                    country=row.get('country') or None
                ))
            except Exception:
                errors += 1
        if objs:
            models.Customer.objects.bulk_create(objs, ignore_conflicts=True)
            created = len(objs)
        report['inserted']['customers'] = created
        report['errors']['customers'] = errors

    def _insert_employees(self, df, report):
        """
        Two-pass insert: create employees without reportsTo, then update reportsTo FK to existing records.
        """
        created = 0; errors = 0
        temp_relations = []
        objs = []
        for _, row in df.iterrows():
            try:
                eid = int(row.get('employeeID')) if row.get('employeeID') else None
                if eid is None:
                    errors += 1; continue
                reports_to_raw = row.get('reportsTo') or None
                objs.append(models.Employee(employeeID=eid,
                                           employeeName=row.get('employeeName') or '',
                                           title=row.get('title') or None,
                                           city=row.get('city') or None,
                                           country=row.get('country') or None,
                                           reportsTo=None))
                temp_relations.append((eid, reports_to_raw))
            except Exception:
                errors += 1
        if objs:
            models.Employee.objects.bulk_create(objs, ignore_conflicts=True)
            created = len(objs)
        # second pass: set reportsTo where possible
        rel_errors = 0
        for eid, reports_to_raw in temp_relations:
            if not reports_to_raw:
                continue
            try:
                reports_to_id = int(reports_to_raw)
                try:
                    manager = models.Employee.objects.get(pk=reports_to_id)
                    emp = models.Employee.objects.get(pk=eid)
                    emp.reportsTo = manager
                    emp.save(update_fields=['reportsTo'])
                except models.Employee.DoesNotExist:
                    rel_errors += 1
            except Exception:
                rel_errors += 1
        report['inserted']['employees'] = created
        report['errors']['employees'] = errors + rel_errors
        report['referential_violations']['employees_reportsTo_missing'] = rel_errors

    def _insert_shippers(self, df, report):
        created = 0; errors = 0
        objs = []
        for _, row in df.iterrows():
            try:
                sid = int(row.get('shipperID')) if row.get('shipperID') else None
                if sid is None:
                    errors += 1; continue
                objs.append(models.Shipper(shipperID=sid, companyName=row.get('companyName') or ''))
            except Exception:
                errors += 1
        if objs:
            models.Shipper.objects.bulk_create(objs, ignore_conflicts=True)
            created = len(objs)
        report['inserted']['shippers'] = created
        report['errors']['shippers'] = errors

    def _insert_products(self, df, report):
        created = 0; errors = 0; ref_violations = 0
        objs = []
        for _, row in df.iterrows():
            try:
                pid = int(row.get('productID')) if row.get('productID') else None
                if pid is None:
                    errors += 1; continue
                cat_raw = row.get('categoryID')
                cat_obj = None
                if cat_raw:
                    try:
                        cat_id = int(cat_raw)
                        cat_obj = models.Category.objects.filter(pk=cat_id).first()
                        if not cat_obj and self.create_missing_parents:
                            cat_obj = models.Category.objects.create(categoryID=cat_id, categoryName=f'Auto-{cat_id}')
                        if not cat_obj:
                            ref_violations += 1
                    except Exception:
                        ref_violations += 1
                discontinued_flag = False
                disc = row.get('discontinued')
                if str(disc).strip().lower() in ['1', 'true', 'yes', 'y']:
                    discontinued_flag = True
                unit_price = None
                try:
                    up = row.get('unitPrice')
                    unit_price = float(up) if up not in (None, '', 'NA', 'NaN') else None
                except Exception:
                    unit_price = None
                objs.append(models.Product(
                    productID=pid,
                    productName=row.get('productName') or '',
                    quantityPerUnit=row.get('quantityPerUnit') or None,
                    unitPrice=unit_price,
                    discontinued=discontinued_flag,
                    category=cat_obj
                ))
            except Exception:
                errors += 1
        if objs:
            models.Product.objects.bulk_create(objs, ignore_conflicts=True)
            created = len(objs)
        report['inserted']['products'] = created
        report['errors']['products'] = errors
        report['referential_violations']['products_category_missing'] = ref_violations

    def _insert_orders(self, df, report):
        created = 0; errors = 0; ref_violations = 0
        objs = []
        for _, row in df.iterrows():
            try:
                oid = int(row.get('orderID')) if row.get('orderID') else None
                if oid is None:
                    errors += 1; continue
                cust_raw = row.get('customerID')
                cust_obj = None
                if cust_raw:
                    cust_obj = models.Customer.objects.filter(pk=cust_raw).first()
                    if not cust_obj and self.create_missing_parents:
                        # create a minimal customer
                        cust_obj = models.Customer.objects.create(customerID=cust_raw, companyName=f'Auto-{cust_raw}')
                    if not cust_obj:
                        ref_violations += 1
                emp_obj = None
                emp_raw = row.get('employeeID')
                if emp_raw:
                    try:
                        emp_obj = models.Employee.objects.filter(pk=int(emp_raw)).first()
                        if not emp_obj:
                            ref_violations += 1
                    except Exception:
                        ref_violations += 1
                shipper_obj = None
                s_raw = row.get('shipperID')
                if s_raw:
                    try:
                        shipper_obj = models.Shipper.objects.filter(pk=int(s_raw)).first()
                        if not shipper_obj:
                            ref_violations += 1
                    except Exception:
                        ref_violations += 1

                order_date = parse_date_safe(row.get('orderDate'))
                required_date = parse_date_safe(row.get('requiredDate'))
                shipped_date = parse_date_safe(row.get('shippedDate'))
                freight = None
                try:
                    freight = float(row.get('freight')) if row.get('freight') not in (None, '', 'NaN') else None
                except Exception:
                    freight = None

                objs.append(models.Order(
                    orderID=oid,
                    customer=cust_obj,
                    employee=emp_obj,
                    orderDate=order_date,
                    requiredDate=required_date,
                    shippedDate=shipped_date,
                    shipper=shipper_obj,
                    freight=freight
                ))
            except Exception:
                errors += 1

        if objs:
            models.Order.objects.bulk_create(objs, ignore_conflicts=True)
            created = len(objs)
        report['inserted']['orders'] = created
        report['errors']['orders'] = errors
        report['referential_violations']['orders_missing_refs'] = ref_violations

    def _insert_order_details(self, df, report):
        created = 0; errors = 0; ref_violations = 0
        objs = []
        for _, row in df.iterrows():
            try:
                oid = int(row.get('orderID')) if row.get('orderID') else None
                pid = int(row.get('productID')) if row.get('productID') else None
                if oid is None or pid is None:
                    errors += 1; continue
                order_obj = models.Order.objects.filter(pk=oid).first()
                product_obj = models.Product.objects.filter(pk=pid).first()
                if not order_obj or not product_obj:
                    ref_violations += 1
                    # skip or create behavior configurable
                    if not (order_obj and product_obj):
                        continue
                unit_price = float(row.get('unitPrice')) if row.get('unitPrice') not in (None, '', 'NaN') else 0.0
                quantity = int(row.get('quantity')) if row.get('quantity') not in (None, '', 'NaN') else 0
                discount = float(row.get('discount')) if row.get('discount') not in (None, '', 'NaN') else 0.0
                objs.append(models.OrderDetail(
                    order=order_obj,
                    product=product_obj,
                    unitPrice=unit_price,
                    quantity=quantity,
                    discount=discount
                ))
            except Exception:
                errors += 1
        if objs:
            # bulk_create could violate unique_together if duplicates exist — ignore_conflicts helps (supported by Postgres)
            models.OrderDetail.objects.bulk_create(objs, ignore_conflicts=True)
            created = len(objs)
        report['inserted']['order_details'] = created
        report['errors']['order_details'] = errors
        report['referential_violations']['order_details_missing_refs'] = ref_violations

# Management command wrapper
class Command(BaseCommand):
    help = 'Load & normalize CSV files into the DB'

    def add_arguments(self, parser):
        parser.add_argument('--csv-root', type=str, help='Root folder where CSV files exist')
        parser.add_argument('--create-missing-parents', action='store_true', help='Auto-create missing parent records when referenced')

    def handle(self, *args, **options):
        csv_root = options.get('csv_root') or getattr(settings, 'CSV_ROOT', None)
        create_missing = bool(options.get('create_missing_parents'))
        loader = CSVLoader(csv_root=csv_root, create_missing_parents=create_missing)
        self.stdout.write("Starting CSV normalization pipeline...")
        report = loader.run()
        self.stdout.write(self.style.SUCCESS("Done. Report:"))
        import json
        self.stdout.write(json.dumps(report, default=str, indent=2))