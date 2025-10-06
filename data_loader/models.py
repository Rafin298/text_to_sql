from django.db import models

class Category(models.Model):
    categoryID = models.IntegerField(primary_key=True)
    categoryName = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'categories'
        indexes = [
            models.Index(fields=['categoryName']),
        ]

    def __str__(self):
        return self.categoryName

class Customer(models.Model):
    customerID = models.CharField(max_length=20, primary_key=True)
    companyName = models.CharField(max_length=255)
    contactName = models.CharField(max_length=255, blank=True, null=True)
    contactTitle = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'customers'
        indexes = [
            models.Index(fields=['companyName']),
            models.Index(fields=['city']),
        ]

    def __str__(self):
        return self.companyName

class Employee(models.Model):
    employeeID = models.IntegerField(primary_key=True)
    employeeName = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    reportsTo = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')

    class Meta:
        db_table = 'employees'
        indexes = [
            models.Index(fields=['employeeName']),
        ]

    def __str__(self):
        return self.employeeName

class Shipper(models.Model):
    shipperID = models.IntegerField(primary_key=True)
    companyName = models.CharField(max_length=255)

    class Meta:
        db_table = 'shippers'
        indexes = [models.Index(fields=['companyName'])]

    def __str__(self):
        return self.companyName

class Product(models.Model):
    productID = models.IntegerField(primary_key=True)
    productName = models.CharField(max_length=255)
    quantityPerUnit = models.CharField(max_length=255, blank=True, null=True)
    unitPrice = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discontinued = models.BooleanField(default=False)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, db_column='categoryID')

    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['productName']),
            models.Index(fields=['category']),
        ]

    def __str__(self):
        return self.productName

class Order(models.Model):
    orderID = models.IntegerField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, db_column='customerID')
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True, db_column='employeeID')
    orderDate = models.DateField(null=True, blank=True)
    requiredDate = models.DateField(null=True, blank=True)
    shippedDate = models.DateField(null=True, blank=True)
    shipper = models.ForeignKey(Shipper, on_delete=models.SET_NULL, null=True, blank=True, db_column='shipperID')
    freight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = 'orders'
        indexes = [
            models.Index(fields=['orderDate']),
            models.Index(fields=['customer']),
        ]

    def __str__(self):
        return f"Order {self.orderID}"

class OrderDetail(models.Model):
    # composite PK (orderID, productID) -- as Django doesn't support composite PK easily.
    # Used an AutoField PK and unique_together to enforce uniqueness.
    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, db_column='orderID', related_name='details')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, db_column='productID')
    unitPrice = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()
    discount = models.FloatField(default=0.0)

    class Meta:
        db_table = 'order_details'
        unique_together = (('order', 'product'),)
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f"Order {self.order_id} - Product {self.product_id}"