from openerp import models, fields, api, _
from openerp import SUPERUSER_ID

class product_template(models.Model):
    """ Add gst Number """
    _inherit = 'product.template'
    _description = 'Add HSN Code(GST)'

    product_hsn_code = fields.Char('HSN Code(GST)')

class product_product(models.Model):
    """ Add gst Number """
    _inherit = 'product.product'
    _description = 'Add HSN Code(GST)'

    product_hsn_code = fields.Char('HSN Code(GST)')

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_hsn_code = fields.Char('HSN Code(GST)')

    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
	
        context = context or {}
        lang = lang or context.get('lang', False)
        if not partner_id:
            raise osv.except_osv(_('No Customer Defined!'), _('Before choosing a product,\n select a customer in the sales form.'))
        warning = False
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        partner = partner_obj.browse(cr, uid, partner_id)
        lang = partner.lang
        context_partner = context.copy()
        context_partner.update({'lang': lang, 'partner_id': partner_id})

        if not product:
            return {'value': {'th_weight': 0,
                'product_uos_qty': qty}, 'domain': {'product_uom': [],
                   'product_uos': []}}
        if not date_order:
            date_order = time.strftime(DEFAULT_SERVER_DATE_FORMAT)

        result = {}
        warning_msgs = ''
        product_obj = product_obj.browse(cr, uid, product, context=context_partner)
	if product_obj:
		result['product_hsn_code'] = product_obj.product_tmpl_id.product_hsn_code
        uom2 = False
        if uom:
            uom2 = product_uom_obj.browse(cr, uid, uom)
            if product_obj.uom_id.category_id.id != uom2.category_id.id:
                uom = False
        if uos:
            if product_obj.uos_id:
                uos2 = product_uom_obj.browse(cr, uid, uos)
                if product_obj.uos_id.category_id.id != uos2.category_id.id:
                    uos = False
            else:
                uos = False

        fpos = False
        if not fiscal_position:
            fpos = partner.property_account_position or False
        else:
            fpos = self.pool.get('account.fiscal.position').browse(cr, uid, fiscal_position)

        if uid == SUPERUSER_ID and context.get('company_id'):
            taxes = product_obj.taxes_id.filtered(lambda r: r.company_id.id == context['company_id'])
        else:
            taxes = product_obj.taxes_id
        result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, fpos, taxes, context=context)

        if not flag:
            result['name'] = self.pool.get('product.product').name_get(cr, uid, [product_obj.id], context=context_partner)[0][1]
            if product_obj.description_sale:
                result['name'] += '\n'+product_obj.description_sale
        domain = {}
        if (not uom) and (not uos):
            result['product_uom'] = product_obj.uom_id.id
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
                uos_category_id = product_obj.uos_id.category_id.id
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
                uos_category_id = False
            result['th_weight'] = qty * product_obj.weight
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],
                        'product_uos':
                        [('category_id', '=', uos_category_id)]}
        elif uos and not uom: # only happens if uom is False
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id
            result['product_uom_qty'] = qty_uos / product_obj.uos_coeff
            result['th_weight'] = result['product_uom_qty'] * product_obj.weight
        elif uom: # whether uos is set or not
            default_uom = product_obj.uom_id and product_obj.uom_id.id
            q = product_uom_obj._compute_qty(cr, uid, uom, qty, default_uom)
            if product_obj.uos_id:
                result['product_uos'] = product_obj.uos_id.id
                result['product_uos_qty'] = qty * product_obj.uos_coeff
            else:
                result['product_uos'] = False
                result['product_uos_qty'] = qty
            result['th_weight'] = q * product_obj.weight        # Round the quantity up

        if not uom2:
            uom2 = product_obj.uom_id
        # get unit price

        if not pricelist:
            warn_msg = _('You have to select a pricelist or a customer in the sales form !\n'
                    'Please set one before choosing a product.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            ctx = dict(
                context,
                uom=uom or result.get('product_uom'),
                date=date_order,
            )
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, qty or 1.0, partner_id, ctx)[pricelist]
            if price is False:
                warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                price = self.pool['account.tax']._fix_tax_included_price(cr, uid, price, taxes, result['tax_id'])
                result.update({'price_unit': price})
                if context.get('uom_qty_change', False):
                    values = {'price_unit': price}
                    for field in ['product_uos_qty', 'th_weight']:
                        if not result.get(field, False) is False:
                            values[field] = result[field]
                    return {'value': values, 'domain': {}, 'warning': False}
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        return {'value': result, 'domain': domain, 'warning': warning}


