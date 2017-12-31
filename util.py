"""
    based on util.py from omgifol, mostly for the binary struct support
"""

from __future__  import print_function
from struct      import pack, unpack, Struct
import six

#----------------------------------------------------------------------
#
# Functions for processing lump names and other strings
#

def zpad(chars):
    """Pad a string with zero bytes, up until a length of 8.
    The string is truncated if longer than 8 bytes."""
    return pack('8s', six.b(chars))
    
def zstrip(chars):
    """
    Return a string representing chars with all trailing null bytes removed.
    chars can be a string or byte string.
    """
    if isinstance(chars, bytes):
        chars = str(chars.decode('ascii', 'ignore'))
    
    if '\0' in chars:
        return chars[:chars.index("\0")]
    return chars

def unpack16(s):
    """Convert a packed signed short (2 bytes) to a Python int"""
    return unpack('<h', s)[0]

def pack16(n):
    """Convert a Python int to a packed signed short (2 bytes)"""
    return pack('<h', n)

def unpack32(s):
    """Convert a packed signed long (4 bytes) to a Python int"""
    return unpack('<i', s)[0]

def pack32(n):
    """Convert a Python int to a packed signed long (4 bytes)"""
    return pack('<i', n)


#----------------------------------------------------------------------
#
# A class/metaclass that can generate "Struct" classes for packing, 
# unpacking, and representing the unpacked form of binary data.
# See omg.mapedit and omg.txdef for usage examples.
#
# Replaces make_struct from 0.3.0 and earlier
#

class StructMeta(type):

	__bits__ = {}

	@staticmethod
	def _get(f):
		# Get struct field or default value
		def fn(self):
			return self._values[f[0]]
		return fn
		
	@staticmethod
	def _set(f):
		# Set struct field, stripping null bytes from string fields
		def fn(self, value):
			if 's' in f[1]:
				self._values[f[0]] = zstrip(value)
			else:
				self._values[f[0]] = value
		return fn

	@property
	def size(cls):
		return cls._struct.size
	
	def __len__(cls):
		return cls._struct.size
	
	def __new__(cls, name, bases, dict):
	
		fields = dict.get("__fields__", [])
		
		# Set up attributes for all defined fields
		for f in fields:
			field_name = f[0]
			field_doc  = f[3] if len(f) > 3 else None
			if 'x' not in f[1]:
				dict[field_name] = property(StructMeta._get(f), StructMeta._set(f), doc = field_doc)
		
		# TODO: set up optional bitfields also (for linedef flags, etc)
		
		# Set up struct format string and size
		dict["_keys"] = [f[0] for f in fields if 'x' not in f[1]]
		dict["_struct"] = Struct("<" + "".join(f[1] for f in fields if f[1]))
		
		return type.__new__(cls, name, bases, dict)

# Python 2 and 3 metaclass hack
_StructParent = StructMeta("_StructParent", (object,), {})

class MapStruct(_StructParent):
	"""
	Class which allows easily creating additional classes based on binary structs.
	
	Create a subclass of Struct with an attribute called __fields__.
	This is a list consisting of tuples with the following info:
	 - name: the name of a struct field
	 - type: the type of the field, such as 'h' or '8s' (see Python's 'struct' module)
	   TODO: if type is 'x' (filler bytes), no property will be created (name can be None).
	   TODO: if type is None, a property will be created but its value will not be packed/unpacked.
	 - value: default value to use
	 - docstring (optional)
	
	Class properties will be automatically generated for all struct members.
	Strings (type 's') will be padded with null bytes on packing, or stripped on unpacking.
	Since this is Doom WAD stuff, some string sanitization will also happen (and they'll
	always be padded to 8 chars since it's assumed to be a lump name).
	
	The 'pack' and 'unpack' methods convert a struct instance to/from binary data.
	"""
	
	def __init__(self, *args, **kwargs):
		"""
		Create a new instance of this struct.
		Arguments can be either positional (based on the layout of the struct),
		and/or keyword arguments based on the names of the struct members.
		
		Other optional arguments:
		'bytes' - a bytestring. The struct will be unpacked from this data
			(other args will be ignored.)
		"""
		# default values (including non-stored properties)
		self._values = dict([(f[0], f[2]) for f in self.__fields__])
		if 'bytes' in kwargs:
			self.unpack(kwargs['bytes'])
		else:
			# args
			values = {}
			values.update(dict(zip(self._keys, args)))
			values.update(kwargs)
			for key, value in values.items():
				if key in self._keys:
					setattr(self, key, value)
	
	def pack(self):
		packs = []
		for f in self.__fields__:
			if 's' in f[1]:
				packs.append(zpad(getattr(self, f[0])))
			elif f[0] in self._keys:
				packs.append(getattr(self, f[0]))
		return self._struct.pack(*packs)

	def unpack(self, data):
		for key, value in zip(self._keys, self._struct.unpack(data)):
			setattr(self, key, value)

	def __eq__(self, other):
		return isinstance(other, self.__class__) and self._values == other._values
	
	def __ne__(self, other):
		return not self.__eq__(other)
	
	def __str__(self):
		return ", ".join(["{0}={1}".format(f[0], self._values[f[0]]) for f in self.__fields__])
	
	def __repr__(self):
		return repr(self._values)
	
	@property
	def size(self):
		return self._struct.size
	
	def __len__(self):
		return self._struct.size
