from flask import current_app
from sqlalchemy.orm import backref

from ...db import (
    sa, CRUDMixin, ProfileMixin, string_property,
    float_property, array_property, integer_property
)
from ..constants import Role
from ...utils import class_property
from ..commodity.models import Commodity


class DealerXUser(sa.Model):
    __tablename__ = 'dealer_x_user'

    dealer_id = sa.Column(sa.BigInteger(), sa.ForeignKey('dealers.id'),
                          primary_key=True, nullable=False)
    users_id = sa.Column(sa.BigInteger(), sa.ForeignKey('users.id'),
                         primary_key=True, nullable=False)


class Dealer(CRUDMixin, ProfileMixin, sa.Model):
    __tablename__ = 'dealers'

    name = sa.Column(sa.Unicode())
    active = sa.Column(sa.Boolean(), nullable=False, default=True)
    users = sa.relationship('User', secondary=DealerXUser.__table__,
                            backref=backref('dealer', uselist=False))
    parent_id = sa.Column(sa.BigInteger(), sa.ForeignKey('dealers.id'))

    @string_property
    def manager(self):
        pass

    @string_property
    def tel(self):
        pass

    @string_property
    def address(self):
        pass

    @string_property
    def dms_code(self):
        pass

    @string_property
    def ims_code(self):
        pass

    @string_property
    def ims_dealer_no(self):
        pass

    @float_property
    def longitude(self):
        pass

    @float_property
    def latitude(self):
        pass

    @array_property
    def contacts(self):
        """
        A list of Contacts to get service SMS.
        Each contact contains the identity and mobile.
        """
        pass

    @property
    def contacts_mobiles(self):
        return ','.join([c['mobile'] for c in self.contacts])

    @string_property
    def yy_seller_user_id(self):
        pass

    @yy_seller_user_id.after_get
    def yy_seller_user_id(self, val):
        if current_app.config['DEBUG']:
            return 'NBJR401'

    @string_property
    def consignee_name(self):
        pass

    @string_property
    def consignee_mobile(self):
        pass

    @string_property
    def consignee_email(self):
        pass

    @string_property
    def consignee_province(self):
        pass

    @string_property
    def consignee_city(self):
        pass

    @string_property
    def consignee_county(self):
        pass

    @string_property
    def consignee_town(self):
        pass

    @string_property
    def consignee_address(self):
        pass

    @string_property
    def consignee_postcode(self):
        pass

    @string_property
    def start_at(self):
        return '09:00'

    @string_property
    def end_at(self):
        return '19:00'

    @integer_property
    def last_ims_order_no(self):
        pass

    @property
    def user(self):
        if self.users:
            return self.users[0]

    @user.setter
    def user(self, val):
        self.users = [val]

    def dt_dump(self):
        rv = self.dump()
        rv.update(dict(
            account=self.users[0].account if self.users else None,
            contacts=self.contacts,
        ))
        if Role.is_it or Role.is_bu:
            rv.update(dict(
                dms_code=self.dms_code,
                ims_code=self.ims_code,
            ))
        return rv

    def dump(self):
        return dict(
            id=self.id,
            name=self.name,
            manager=self.manager,
            address=self.address,
            tel=self.tel,
            active=self.active,
            longitude=self.longitude,
            latitude=self.latitude,
            sales=self.sales,
            start_at=self.start_at,
            end_at=self.end_at,
        )

    @property
    def sales(self):
        return sa.session.query(sa.func.sum(Commodity.sales)).filter(
            Commodity.dealer_id == self.id).scalar()

    @class_property
    def picker_data(cls):
        return [
            dict(name=i.name, value=f'{i.id}') for i in cls.query.filter(
                cls.active.is_(True)
            )
        ]
