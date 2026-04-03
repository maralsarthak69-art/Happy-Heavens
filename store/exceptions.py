class InsufficientStockError(Exception):
    """Raised when a cart item's requested quantity exceeds available Product.stock."""

    def __init__(self, product):
        self.product = product
        super().__init__(
            f'Insufficient stock for "{product.name}": '
            f'only {product.stock} unit(s) available.'
        )
