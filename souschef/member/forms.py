from datetime import datetime
import json

from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from souschef.member.formsfield import CAPhoneNumberExtField
from localflavor.ca.forms import CAPostalCodeField
from souschef.meal.models import (
    Ingredient, Component, COMPONENT_GROUP_CHOICES,
    Restricted_item, COMPONENT_GROUP_CHOICES_SIDES
)
from souschef.order.models import SIZE_CHOICES
from souschef.member.models import (
    Member, Client, RATE_TYPE, Option,
    GENDER_CHOICES, PAYMENT_TYPE, DELIVERY_TYPE,
    DAYS_OF_WEEK, Route, ClientScheduledStatus,
    Relationship
)


class ClientBasicInformation (forms.Form):

    firstname = forms.CharField(
        max_length=100,
        label=_("First Name"),
        widget=forms.TextInput(attrs={'placeholder': _('First name')})
    )

    lastname = forms.CharField(
        max_length=100,
        label=_("Last Name"),
        widget=forms.TextInput(attrs={'placeholder': _('Last name')})
    )

    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'ui dropdown'})
    )

    language = forms.ChoiceField(
        choices=Client.LANGUAGES,
        label=_("Preferred language"),
        widget=forms.Select(attrs={'class': 'ui dropdown'})
    )

    birthdate = forms.DateField(
        label=_("Birthday"),
        widget=forms.TextInput(
            attrs={
                'class': 'ui calendar',
                'placeholder': _('YYYY-MM-DD')
            }
        ),
        help_text=_('Format: YYYY-MM-DD'),
    )

    email = forms.EmailField(
        max_length=100,
        label='<i class="email icon"></i>',
        widget=forms.TextInput(attrs={'placeholder': _('Email')}),
        required=False,
    )

    home_phone = CAPhoneNumberExtField(
        label='Home',
        widget=forms.TextInput(attrs={'placeholder': _('Home phone')}),
        required=False,
    )

    cell_phone = CAPhoneNumberExtField(
        label='Cell',
        widget=forms.TextInput(attrs={'placeholder': _('Cellular')}),
        required=False,
    )

    alert = forms.CharField(
        label=_("Alert"),
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': _('Your message here ...')
        })
    )

    def clean(self):
        if not (self.cleaned_data.get('email') or
                self.cleaned_data.get('home_phone') or
                self.cleaned_data.get('cell_phone')):
            msg = _('At least one contact information is required.')
            self.add_error('email', msg)
            self.add_error('home_phone', msg)
            self.add_error('cell_phone', msg)

        return self.cleaned_data


class ClientAddressInformation(forms.Form):

    apartment = forms.CharField(
        label=_("Apt #"),
        widget=forms.TextInput(attrs={
            'placeholder': _('Apt #'),
            'class': 'apartment'
        }),
        required=False
    )

    street = forms.CharField(
        max_length=100,
        label=_("Address Information"),
        widget=forms.TextInput(attrs={
            'placeholder': _('7275 Rue Saint-Urbain'),
            'class': 'street name'
        })
    )

    city = forms.CharField(
        max_length=50,
        label=_("City"),
        widget=forms.TextInput(attrs={
            'placeholder': _('Montreal'),
            'class': 'city'
        })
    )

    postal_code = CAPostalCodeField(
        max_length=7,
        label=_("Postal Code"),
        widget=forms.TextInput(attrs={
            'placeholder': _('H2R 2Y5'),
            'class': 'postal code'
        })
    )

    latitude = forms.CharField(
        label=_('Latitude'),
        required=False,
        initial=0,
        widget=forms.TextInput(attrs={'class': 'latitude'})
    )

    longitude = forms.CharField(
        label=_('Longitude'),
        required=False,
        initial=0,
        widget=forms.TextInput(attrs={'class': 'longitude'})
    )

    distance = forms.CharField(
        label=_('Distance from Santropol'),
        required=False,
        initial=0,
        widget=forms.TextInput(attrs={'class': 'distance'})
    )

    route = forms.ModelChoiceField(
        label=_('Route'),
        required=True,
        widget=forms.Select(attrs={'class': 'ui search dropdown'}),
        queryset=Route.objects.all(),
    )

    delivery_note = forms.CharField(
        label=_("Delivery Note"),
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 2,
            'placeholder': _('Delivery Note here ...')
        })
    )


class ClientRestrictionsInformation(forms.Form):

    def __init__(self, *args, **kwargs):
        super(ClientRestrictionsInformation, self).__init__(*args, **kwargs)

        for day, translation in DAYS_OF_WEEK:
            self.fields['size_{}'.format(day)] = forms.ChoiceField(
                choices=SIZE_CHOICES,
                widget=forms.Select(),
                required=False
            )

            for meal, meal_translation in COMPONENT_GROUP_CHOICES:
                if meal is COMPONENT_GROUP_CHOICES_SIDES:
                    continue  # skip "Sides"
                self.fields['{}_{}_quantity'.format(meal, day)] = \
                    forms.IntegerField(
                        required=False,
                        min_value=0,
                        widget=forms.TextInput()
                    )

    status = forms.BooleanField(
        label=_('Active'),
        help_text=_('By default, the client meal status is Pending.'),
        required=False,
    )

    delivery_type = forms.ChoiceField(
        label=_('Type'),
        choices=DELIVERY_TYPE,
        required=True,
        widget=forms.Select(attrs={'class': 'ui dropdown'})
    )

    meals_schedule = forms.MultipleChoiceField(
        label=_('Schedule'),
        initial='Select days of week',
        choices=DAYS_OF_WEEK,
        widget=forms.SelectMultiple(attrs={'class': 'ui dropdown'}),
        required=False,
    )

    restrictions = forms.ModelMultipleChoiceField(
        label=_("Restrictions"),
        queryset=Restricted_item.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'ui dropdown search'})
    )

    food_preparation = forms.ModelMultipleChoiceField(
        label=_("Preparation"),
        required=False,
        queryset=Option.objects.filter(option_group='preparation'),
        widget=forms.SelectMultiple(attrs={'class': 'ui dropdown'}),
    )

    ingredient_to_avoid = forms.ModelMultipleChoiceField(
        label=_("Ingredient To Avoid"),
        queryset=Ingredient.objects.all(),
        required=False,
        widget=forms.SelectMultiple(
            attrs={'class': 'ui dropdown search'}
        )
    )

    dish_to_avoid = forms.ModelMultipleChoiceField(
        label=_("Dish(es) To Avoid"),
        queryset=Component.objects.all(),
        required=False,
        widget=forms.SelectMultiple(
            attrs={'class': 'ui dropdown search'}
        )
    )

    cancel_meal_dates = forms.CharField(
        required=False,
        label=_('Cancel dates'),
    )

    def clean(self):
        """
        The meal defaults are required for the scheduled delivery days:
        at least one of the quantities should be set.
        This only applies to ongoing clients!

        Regardless of meal schedules, when a main dish is set, we should
        enforce the setting of its size.
        """
        super(ClientRestrictionsInformation, self).clean()

        def to_cancel_date(str_date):
            return datetime.strptime(
                str_date, "%Y-%m-%d"
            ).date()

        if self.cleaned_data.get('cancel_meal_dates'):
            self.cleaned_data['cancel_meal_dates'] = list(map(to_cancel_date,
                                                              json.loads(self.cleaned_data['cancel_meal_dates'])))


        if self.cleaned_data.get('delivery_type') == 'O':
            # Ongoing
            meals_schedule = self.cleaned_data.get('meals_schedule')
            if meals_schedule is None:
                meals_schedule = []
        else:
            # Episodic
            meals_schedule = []

        day_displays = dict(DAYS_OF_WEEK)

        for day in meals_schedule:
            # At least one of the quantities should be set.
            quantity_fieldnames = []
            for meal, meal_translation in COMPONENT_GROUP_CHOICES:
                if meal is COMPONENT_GROUP_CHOICES_SIDES:
                    continue  # skip "Sides"
                fieldname = '{}_{}_quantity'.format(meal, day)
                quantity_fieldnames.append(fieldname)

            total_quantity = sum(map(
                lambda n: self.cleaned_data.get(n) or 0,
                quantity_fieldnames
            ), 0)
            if total_quantity == 0:
                for n in quantity_fieldnames:
                    self.add_error(
                        n,
                        _("At least one of the quantities should be "
                          "set because %(weekday)s is scheduled for "
                          "delivery.") % {
                              'weekday': day_displays[day]
                          }
                    )

        for day, day_display in DAYS_OF_WEEK:
            # If the main dish is set, size should also be set.
            main_dish_quantity = self.cleaned_data.get(
                'main_dish_{}_quantity'.format(day)
            )
            fieldname_size = 'size_{}'.format(day)
            if main_dish_quantity and not self.cleaned_data.get(
                    fieldname_size
            ):
                self.add_error(
                    fieldname_size,
                    _("Size is required when the main dish is set.")
                )


class MemberForm(forms.Form):

    member = forms.CharField(
        label=_("Member"),
        widget=forms.TextInput(attrs={
            'placeholder': _('Type 3 characters or more to search members'),
            'class': 'prompt existing--member'
        }),
        required=False
    )

    firstname = forms.CharField(
        label=_("First Name"),
        widget=forms.TextInput(attrs={
            'placeholder': _('First Name'),
            'class': 'firstname'
        }),
        required=False
    )

    lastname = forms.CharField(
        label=_("Last Name"),
        widget=forms.TextInput(attrs={
            'placeholder': _('Last Name'),
            'class': 'lastname'
        }),
        required=False
    )

    email = forms.EmailField(
        label='<i class="email icon"></i>',
        widget=forms.TextInput(attrs={'placeholder': _('Email')}),
        required=False,
    )

    work_phone = CAPhoneNumberExtField(
        label='Work',
        widget=forms.TextInput(attrs={'placeholder': _('Work phone')}),
        required=False,
    )

    cell_phone = CAPhoneNumberExtField(
        label='Cell',
        widget=forms.TextInput(attrs={'placeholder': _('Cellular')}),
        required=False,
    )

    def clean(self):
        cleaned_data = super(MemberForm, self).clean()

        """If the client pays for himself. """
        if cleaned_data.get('same_as_client') is True:
            return cleaned_data

        member = cleaned_data.get('member')
        firstname = cleaned_data.get('firstname')
        lastname = cleaned_data.get('lastname')

        if not member and (not firstname or not lastname):
            msg = _('This field is required unless you add a new member.')
            self.add_error('member', msg)
            msg = _(
                'This field is required unless you chose an existing member.'
            )
            self.add_error('firstname', msg)
            self.add_error('lastname', msg)

        if member:
            member_id = member.split(' ')[0].replace('[', '').replace(']', '')
            try:
                Member.objects.get(pk=member_id)
            except ObjectDoesNotExist:
                msg = _('Not a valid member, please chose an existing member.')
                self.add_error('member', msg)
        return cleaned_data


class ClientPaymentInformation(MemberForm):

    facturation = forms.ChoiceField(
        label=_("Billing Type"),
        choices=RATE_TYPE,
        widget=forms.Select(attrs={'class': 'ui dropdown'})
    )

    same_as_client = forms.BooleanField(
        label=_("Same As Client"),
        required=False,
        help_text=_('If checked, the personal information '
                    'of the client will be used as billing information.'),
        widget=forms.CheckboxInput(
            attrs={}))

    billing_payment_type = forms.ChoiceField(
        label=_("Payment Type"),
        choices=PAYMENT_TYPE,
        widget=forms.Select(attrs={'class': 'ui dropdown'}),
        required=False
    )

    number = forms.IntegerField(label=_("Street Number"), required=False)

    apartment = forms.CharField(
        label=_("Apt #"),
        widget=forms.TextInput(attrs={'placeholder': _('Apt #')}),
        required=False
    )

    floor = forms.IntegerField(label=_("Floor"), required=False)

    street = forms.CharField(label=_("Street Name"), required=False)

    city = forms.CharField(label=_("City Name"), required=False)

    postal_code = CAPostalCodeField(label=_("Postal Code"), required=False)

    def clean(self):
        cleaned_data = super(ClientPaymentInformation, self).clean()

        if cleaned_data.get('same_as_client') is True:
            return cleaned_data

        member = cleaned_data.get('member')
        if member:
            member_id = member.split(' ')[0].replace('[', '').replace(']', '')
            member_obj = Member.objects.get(pk=member_id)
            if not member_obj.address:
                msg = _('This member has not a valid address, '
                        'please add a valid address to this member, so it can '
                        'be used for the billing.')
                self.add_error('member', msg)
        else:
            msg = _("This field is required")
            fields = ['street', 'city', 'postal_code']
            for field in fields:
                field_data = cleaned_data.get(field)
                if not field_data:
                    self.add_error(field, msg)
        return cleaned_data


class ClientRelationshipInformation(MemberForm):

    nature = forms.CharField(
        label=_("Nature of Relationship"),
        widget=forms.TextInput(
            attrs={'placeholder': _('Doctor, Friend, Daughter, ...')}
        ),
    )

    type = forms.MultipleChoiceField(
        label=_("Type of Relationship"),
        choices=Relationship.TYPE_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={
            'onchange': '$(this).closest(".formset-item.relationship")'
                        '.find(".souschef-referent-only")'
                        '[($(this).closest("ul").find('
                        '        "input[type=checkbox][value=%s]:checked"'
                        '    ).length > 0) ? '
                        ' "show" : "hide"]()' % Relationship.REFERENT,
            'class': 'sc-checkbox-select-multiple'
        }),
        initial=[],
        required=False
    )

    remark = forms.CharField(
        label=_("Remark"),
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )

    # Extra fields
    work_information = forms.CharField(
        max_length=200,
        label=_('Work information'),
        widget=forms.TextInput(attrs={
            'placeholder': _('Hotel-Dieu, St-Anne Hospital, ...')
        }),
        required=False
    )
    referral_date = forms.DateField(
        label=_("Referral Date"),
        widget=forms.TextInput(
            attrs={
                'class': 'ui calendar',
                'placeholder': _('YYYY-MM-DD')
            }
        ),
        help_text=_('Format: YYYY-MM-DD'),
        required=False,
    )
    referral_reason = forms.CharField(
        label=_("Referral Reason"),
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False
    )

    @property
    def has_referent_relationship(self):
        return Relationship.REFERENT in self.cleaned_data.get('type', [])

    def clean(self):
        member = self.cleaned_data.get('member')
        if member:
            member_id = member.split(' ')[0].replace('[', '').replace(']', '')
            try:
                Member.objects.get(pk=member_id)
            except (ObjectDoesNotExist, ValueError):
                msg = _('Not a valid member, please chose an existing member.')
                self.add_error('member', msg)
        else:
            if not self.cleaned_data.get('firstname'):
                msg = _(
                    'This field is required unless '
                    'you chose an existing member.'
                )
                self.add_error('firstname', msg)
            if not self.cleaned_data.get('firstname'):
                msg = _(
                    'This field is required unless '
                    'you chose an existing member.'
                )
                self.add_error('lastname', msg)
            if not (self.cleaned_data.get('email') or
                    self.cleaned_data.get('work_phone') or
                    self.cleaned_data.get('cell_phone')):
                msg = _('At least one contact is required.')
                self.add_error('email', msg)
                self.add_error('work_phone', msg)
                self.add_error('cell_phone', msg)
            if self.has_referent_relationship:
                if not self.cleaned_data.get('work_information'):
                    msg = _('This field is required for a referent '
                            'relationship.')
                    self.add_error('work_information', msg)

        if self.has_referent_relationship:
            if not self.cleaned_data.get('referral_date'):
                msg = _('This field is required for a referent relationship.')
                self.add_error('referral_date', msg)
            if not self.cleaned_data.get('referral_reason'):
                msg = _('This field is required for a referent relationship.')
                self.add_error('referral_reason', msg)
        return self.cleaned_data


class ClientScheduledStatusForm(forms.ModelForm):

    class Meta:
        model = ClientScheduledStatus
        fields = [
            'client', 'status_from', 'status_to', 'reason', 'change_date'
        ]
        widgets = {
            'status_to': forms.Select(attrs={
                'class': 'ui status_to dropdown'
            }),
            'reason': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super(ClientScheduledStatusForm, self).__init__(*args, **kwargs)
        self.fields['end_date'] = forms.DateField(
            required=False,
            widget=forms.TextInput(
                attrs={
                    'class': 'ui calendar',
                    'placeholder': _('YYYY-MM-DD')
                }
            ),
            help_text=_('Format: YYYY-MM-DD'),
        )

    def save(self, *args, **kwargs):
        """
        Override the default behavior of a ModelForm.
        We may have two ClientScheduledStatus instances to save. The .save()
        method is not expressive enough for what we want to do.
        Thus, we raise an error when trying to call form.save() to remind
        other people of using the custom save method.
        """
        raise NotImplementedError(
            "This method is intentionally bypassed. Please use "
            "save_scheduled_statuses method.")

    def save_scheduled_statuses(self, callback_add_message=lambda m: None):
        """
        Create one or two ClientScheduledStatus instances according to
        `self.cleaned_data`.
        """
        if not hasattr(self, 'cleaned_data') or self.errors:
            raise ValueError("The form data doesn't validate.")
        data = self.cleaned_data
        today = timezone.datetime.date(timezone.datetime.today())

        # Save and process instance(s)
        c1 = ClientScheduledStatus.objects.create(
            client=data['client'],
            status_from=data['status_from'],
            status_to=data['status_to'],
            reason=data['reason'],
            change_date=data['change_date'],
            change_state=ClientScheduledStatus.END,
            operation_status=ClientScheduledStatus.TOBEPROCESSED
        )
        if data['change_date'] == today:
            c1.process()
            callback_add_message(_("The client status has been changed."))
        else:
            callback_add_message(_("This status change has been scheduled."))

        if data.get('end_date'):
            c2 = ClientScheduledStatus.objects.create(
                client=data['client'],
                status_from=data['status_to'],
                status_to=data['status_from'],
                reason=data['reason'],
                change_date=data['end_date'],
                change_state=ClientScheduledStatus.END,
                operation_status=ClientScheduledStatus.TOBEPROCESSED,
                pair=c1
            )
            if data.get('end_date') == today:
                c2.process()
                callback_add_message(_("The client status has been changed."))
            else:
                callback_add_message(_("The end date of this status change "
                                       "has been scheduled."))
