# encoding: utf-8

"""TurboMail utility functions and support classes."""

from __future__ import unicode_literals
import sys

from email.utils import formataddr, parseaddr
from email.header import Header

from marrow.mailer.validator import EmailValidator
from marrow.util.compat import basestring, unicode, unicodestr

__all__ = ['Address', 'AddressList']


class Address(object):
    """Validated electronic mail address class.
    
    This class knows how to validate and format e-mail addresses.  It uses
    Python's built-in `parseaddr` and `formataddr` helper functions and helps
    guarantee a uniform base for all e-mail address operations.
    
    The AddressList unit tests provide comprehensive testing of this class as
    well."""
    
    def __init__(self, name_or_email, email=None, encoding='utf-8'):
        if email is None:
            if isinstance(name_or_email, AddressList):
                if not 0 < len(name_or_email) < 2:
                    raise ValueError("AddressList to convert must only contain a single Address.")
                
                name_or_email = unicode(name_or_email[0])
            
            if isinstance(name_or_email, (tuple, list)):
                self.name = unicodestr(name_or_email[0], encoding)
                self.address = unicodestr(name_or_email[1], encoding)
            
            elif isinstance(name_or_email, bytes):
                self.name, self.address = parseaddr(unicodestr(name_or_email, encoding))
            
            elif isinstance(name_or_email, unicode):
                self.name, self.address = parseaddr(name_or_email)
            
            else:
                raise TypeError('Expected string, tuple or list, got {0} instead'.format(
                        repr(type(name_or_email))
                    ))
        else:
            self.name = unicodestr(name_or_email, encoding)
            self.address = unicodestr(email, encoding)
        
        email, err = EmailValidator().validate_email(self.address)
        
        if err:
            raise ValueError('"{0}" is not a valid e-mail address: {1}'.format(email, err))
    
    def __eq__(self, other):
        if isinstance(other, Address):
            return (self.name, self.address) == (other.name, other.address)
        
        elif isinstance(other, unicode):
            return unicode(self) == other
        
        elif isinstance(other, bytes):
            return bytes(self) == other
        
        elif isinstance(other, tuple):
            return (self.name, self.address) == other
        
        raise NotImplementedError("Can not compare Address instance against {0} instance".format(type(other)))
    
    def __ne__(self, other):
        return not self == other
    
    def __len__(self):
        return len(unicode(self))
    
    def __repr__(self):
        return 'Address("%s")' % self
    
    def __unicode__(self):
        return formataddr((self.name, self.address))
    
    def __bytes__(self):
        return self.encode()
    
    if sys.version_info < (3, 0):
        __str__ = __bytes__
    
    else:  # pragma: no cover
        __str__ = __unicode__
    
    def encode(self, encoding='utf-8'):
        name_string = unicode(Header(self.name, encoding))
        
        # Encode punycode for internationalized domains.
        localpart, domain = self.address.split('@', 1)
        domain = domain.encode('idna').decode()
        address = '@'.join((localpart, domain))
        
        return formataddr((name_string, address)).replace('\n', '').encode(encoding)
    
    @property
    def valid(self):
        email, err = EmailValidator().validate_email(self.address)
        return bool(err)


class AddressList(list):
    def __init__(self, addresses=None, encoding="utf-8"):
        super(AddressList, self).__init__()
        
        self.encoding = encoding
        
        if addresses is None:
            return
        
        if isinstance(addresses, basestring):
            addresses = addresses.split(',')
        
        elif isinstance(addresses, tuple):
            self.append(Address(addresses, encoding=encoding))
            return
        
        if not isinstance(addresses, list):
            raise ValueError("Invalid value for AddressList: {0}".format(repr(addresses)))
        
        self.extend(addresses)
    
    def __repr__(self):
        if not self:
            return "AddressList()"
        
        return "AddressList(\"{0}\")".format(self)
    
    def __bytes__(self):
        return self.encode()
    
    def __unicode__(self):
        return ", ".join(str(i) for i in self)
    
    if sys.version_info < (3, 0):
        __str__ = __bytes__
    
    else:  # pragma: no cover
        __str__ = __unicode__
    
    def __setitem__(self, k, value):
        if isinstance(k, slice):
            value = [Address(val) if not isinstance(val, Address) else val for val in value]
        
        elif not isinstance(value, Address):
            value = Address(value)
        
        super(AddressList, self).__setitem__(k, value)
    
    def __setslice__(self, i, j, sequence):
        self.__setitem__(slice(i, j), sequence)
    
    def encode(self, encoding=None):
        encoding = encoding if encoding else self.encoding
        return b", ".join(a.encode(encoding) for a in self)
    
    def extend(self, sequence):
        values = [Address(val) if not isinstance(val, Address) else val for val in sequence]
        super(AddressList, self).extend(values)
    
    def append(self, value):
        self.extend([value])
    
    @property
    def addresses(self):
        return AddressList([i.address for i in self])
    
    @property
    def string_addresses(self, encoding=None):
        """Return a list of string representations of the addresses suitable
        for usage in an SMTP transaction."""
        encoding = encoding if encoding else self.encoding
        return [a.encode(encoding) for a in AddressList([i.address for i in self])]


class AutoConverter(object):
    """Automatically converts an assigned value to the given type."""

    def __init__(self, cls, default=None):
        self.cls = cls
        
        if hasattr(default, '__call__'):
            default = default()
        
        self.value = default

    def __get__(self, instance, owner):
        return self.value

    def __set__(self, instance, value):
        if not isinstance(value, self.cls):
            value = self.cls(value)
        self.value = value

    def __delete__(self, instance):
        del self.value
