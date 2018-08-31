#coding: utf-8

import hashlib
import types

class Lazy:
	"""Decorator for endpoint objects lazifying.

	Arguments:
	----------
	cache -- dict-like object, which stores and loads evaluation's results (f.e. DirCache or dict)
	algo -- hashing algorithm for keys making. (hashlib-like)
	encache -- default state of enabling caching operations
	diag -- diagnostic output
	"""

	def __init__(self, cache, algo = hashlib.sha256, encache = True, diag = False):
		self.cache = cache
		self.algo = algo
		self.encache = encache
		self.diag = diag

	def __call__(self, func):
		"""Construct lazy wrap for callable or another type object."""
		return LazyGeneric(self, func)

class LazyObject:
	"""Lazytree element's interface.

	A lazy object provides a rather abstract interface. We can use attribute getting or operators to
	generate another lazy objects.

	The technical problem is that a lazy wrapper does not know the type of wraped object before unlazing.
	Therefore, we assume that any action on a lazy object is a priori true. If the object does not support 
	the manipulation performed on it, we will know about it at the execution stage.
	
	Arguments:
	----------
	lazifier -- parental lazy decorator
	"""

	def __init__(self, lazifier, encache = None): 
		self.__lazybase__ = lazifier
		self.__encache__ = encache if encache != None else self.__lazybase__.encache

	def __call__(self, *args, **kwargs): return LazyResult(self.__lazybase__, self, args, kwargs)
	
	def __getattr__(self, item): return LazyResult(self.__lazybase__, getattr, (self, item), encache = False)
	def __getitem__(self, item): return LazyResult(self.__lazybase__, lambda x, i: x[i], (self, item))

	def __add__(self, oth): return LazyResult(self.__lazybase__, lambda x,y: x + y, (self, oth))
	def __sub__(self, oth): return LazyResult(self.__lazybase__, lambda x,y: x - y, (self, oth))
	def __xor__(self, oth): return LazyResult(self.__lazybase__, lambda x,y: x ^ y, (self, oth))
	def __mul__(self, oth): return LazyResult(self.__lazybase__, lambda x,y: x * y, (self, oth))
	def __div__(self, oth): return LazyResult(self.__lazybase__, lambda x,y: x / y, (self, oth))

	def __eq__(self, oth): return LazyResult(self.__lazybase__, lambda x,y: x == y, (self, oth))
	def __ne__(self, oth): return LazyResult(self.__lazybase__, lambda x,y: x != y, (self, oth))
	def __lt__(self, oth): return LazyResult(self.__lazybase__, lambda x,y: x <  y, (self, oth))
	def __le__(self, oth): return LazyResult(self.__lazybase__, lambda x,y: x <= y, (self, oth))
	def __gt__(self, oth): return LazyResult(self.__lazybase__, lambda x,y: x >  y, (self, oth))
	def __ge__(self, oth): return LazyResult(self.__lazybase__, lambda x,y: x >= y, (self, oth))

	def unlazy(self):
		"""Get a result of evaluation.

		See .unlazy function for details.
		
		Disclamer:
		Technically, the evaluated object can define an "unlazy" method.
		If so, we'll hide such the method. However since using the unlazy 
		function is more convenient as the method, so this option was excluded."""		
		ret = unlazy(self)
		if hasattr(ret, "unlazy"):
			print("WARNING: Shadow unlazy method.")
		return ret

class LazyResult(LazyObject):
	"""Derived lazy object.

	Can be constructed with another LazyObject methods.

	Arguments:
	----------
	lazifier -- parental lazy decorator
	generic -- callable used for object evaluation
	args -- arguments used for object evaluation
	kwargs -- keyword arguments used for object evaluation
	"""

	def __init__(self, lazifier, generic, args = (), kwargs = {}, encache = None):
		LazyObject.__init__(self, lazifier, encache)	
		self.generic = generic
		self.args = args
		self.kwargs = kwargs
		self.__lazyvalue__ = None
		
		m = self.__lazybase__.algo()		
		updatehash(m, self.generic)
		if len(args): updatehash(m, args)
		if len(kwargs): updatehash(m, kwargs)

		self.__lazyhash__ = m.digest()
		self.__lazyhexhash__ = m.hexdigest()

	def __repr__(self): return "<LazyResult(generic:{},args:{},kwargs:{})>".format(self.generic, self.args, self.kwargs)

class LazyGeneric(LazyObject):
	"""Lazy function wraper.

	End point of lazy tree. Special LazyObject type to wrap
	function, methods, ctors, functors or another noncallable objects...
	It constructed in Lazy.__call__.

	Arguments:
	----------
	lazifier -- parental lazy decorator
	func -- wrapped callable
	"""

	def __init__(self, lazifier, wrapped_object):
		LazyObject.__init__(self, lazifier, encache = False)
		self.__lazyvalue__ = wrapped_object
		
		m = self.__lazybase__.algo()
		updatehash(m, wrapped_object)
		
		self.__lazyhash__ = m.digest()
		self.__lazyhexhash__ = m.hexdigest()

	def __get__(self, instance, cls):
		"""With __get__ method we can use lazy decorator on class's methods"""
		if instance != None and isinstance(self.__lazyvalue__, types.FunctionType):
			return types.MethodType(self, instance)
		else:
			return self

	def __repr__(self): return "<LazyGeneric(value:{})>".format(self.__lazyvalue__)

def lazydo(obj):
	"""Perform evaluation.

	We need expand all arguments and callable for support lazy trees."""
	func = expand(obj.generic)
	args = expand(obj.args)
	kwargs = expand(obj.kwargs)

	##We showld expand result becouse it can be LazyObject
	result = expand(func(*args, **kwargs)) 
	return result

def unlazy(obj):
	"""Get a result of evaluation.

	This function searches for the result in local memory (fget), and after that in cache (load).
	If object wasn't stored early, it performs evaluation and stores a result in cache and local memory (save).
	"""
	diagnostic = obj.__lazybase__.diag
	if (obj.__lazyvalue__ != None):
		if diagnostic: print('endp' if isinstance(obj, LazyGeneric) else 'fget', obj.__lazyhexhash__)				
	elif obj.__lazyhexhash__ in obj.__lazybase__.cache:
		if diagnostic: print('load', obj.__lazyhexhash__)
		obj.__lazyvalue__ = obj.__lazybase__.cache[obj.__lazyhexhash__]
	else:
		obj.__lazyvalue__ = lazydo(obj)		
		if obj.__encache__:
			if diagnostic: print('save', obj.__lazyhexhash__)
			obj.__lazybase__.cache[obj.__lazyhexhash__] = obj.__lazyvalue__
		else:
			if diagnostic: print('eval', obj.__lazyhexhash__)
	return obj.__lazyvalue__					

def expand(arg):
	"""Apply unlazy operation for argument or for all argument's items if need."""
	if isinstance(arg, list) or isinstance(arg, tuple): return [ expand(a) for a in arg ] 
	elif isinstance(arg, dict) : return { k : expand(v) for k, v in arg.items() }
	else: return unlazy(arg) if isinstance(arg, LazyObject) else arg

def updatehash_list(m, obj):
	for e in obj:
		updatehash(m, e)

def updatehash_dict(m, obj):
	for k, v in sorted(obj.items()):
		updatehash(m, k)
		updatehash(m, v)

def updatehash_LazyObject(m, obj):
	m.update(obj.__lazyhash__)

def updatehash_function(m, obj):
	if hasattr(obj, "__qualname__"): 
		m.update(obj.__qualname__.encode("utf-8"))
	elif hasattr(obj, "__name__") : 
		m.update(obj.__name__.encode("utf-8"))
	if hasattr(obj, "__module__") and obj.__module__: 
		m.update(obj.__module__.encode("utf-8"))

## Table of hash functions for special types.
hashfuncs = {
	LazyGeneric: updatehash_LazyObject,
	LazyResult: updatehash_LazyObject,
	tuple: updatehash_list,
	list: updatehash_list,
	dict: updatehash_dict,
	types.FunctionType: updatehash_function,
}

def updatehash(m, obj):
	"""Update hash in hashlib-like algo with hashable object

	As usual we use hash of object representation, but for special types we can set
	special updatehash functions (see 'hashfuncs' table).

	Warn: If you use changing between program starts object representation (f.e. object.__repr__)
	for hashing, this library will not be work corectly. 

	Arguments
	---------
	m -- hashlib-like algorithm instance.
	obj -- hashable object
	"""
	if obj.__class__ in hashfuncs:
		hashfuncs[obj.__class__](m, obj)
	else:
		if obj.__class__.__repr__ == object.__repr__:
			print("WARNING: object of class {} uses common __repr__ method. Сache may not work correctly"
				.format(obj.__class__))
		m.update(repr(obj).encode("utf-8"))

__tree_tab = "    "
def print_tree(obj, t = 0):
	"""Print lazy tree in user friendly format."""	
	if isinstance(obj, LazyResult):
		print(__tree_tab*t, end=''); print("LazyResult:")
		print(__tree_tab*t, end=''); print("|generic:\n", end=''); print_tree(obj.generic, t+1)
		if (len(obj.args)): print(__tree_tab*t, end=''); print("|args:\n", end=''); print_tree(obj.args, t+1)
		if (len(obj.kwargs)): print(__tree_tab*t, end=''); print("|kwargs:\n", end=''); print_tree(obj.kwargs, t+1)
		print(__tree_tab*t, end=''); print("-------")
	elif isinstance(obj, list) or isinstance(obj, tuple):
		for o in obj:
			print_tree(o, t)
	else:
		print(__tree_tab*t, end=''); print(obj)

def encache(obj, sts):
	obj.__encache__ = sts