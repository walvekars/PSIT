from openerp import models, fields, api, exceptions, _
import openerp.addons.decimal_precision as dp
from openerp.tools import amount_to_text_en
import pdb

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def convert(self, amount, cur='INR'):
    	amt_en = amount_to_text_en.amount_to_text(amount, 'en', cur)
    	return amt_en
