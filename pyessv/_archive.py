# -*- coding: utf-8 -*-

"""
.. module:: pyessv._archive.py
   :copyright: Copyright "December 01, 2016", IPSL
   :license: GPL/CeCIL
   :platform: Unix, Windows
   :synopsis: Encapsulates access to archive.

.. moduleauthor:: Mark Conway-Greenslade <momipsl@ipsl.jussieu.fr>


"""
import random
import uuid

from pyessv._cache import cache
from pyessv._cache import get_cached
from pyessv._io_manager import write
from pyessv._model import Authority
from pyessv._model import Term
from pyessv._utils.formatter import format_canonical_name
from pyessv._utils.formatter import format_string

from pyessv._factory import create_term



def load(*args):
    """Loads a vocabulary node from archive.

    :param str identifier: Vocabulary node identifier.

    :return: A vocabulary node.
    :rtype: pyessv.Node | None

    """
    assert len(args) >= 1 and len(args) <= 4, 'Vocabs can be loaded by namespace, uuid & name'
    if len(args) == 1:
        node = _load_by_namespace(args[0])
        if node is None:
            node = _load_by_uid(args[0])
    else:
        node = _load_by_name(args)

    return node


def _load_by_name(args):
    """Loads a vocabulary node from archive by name.

    :param str authority: Vocabulary authority, e.g. wcrp.
    :param str scope: Vocabulary scope, e.g. global.
    :param str collection: Vocabulary collection, e.g. institute-id.
    :param str term: Vocabulary term, e.g. ipsl.

    :return: A vocabulary node.
    :rtype: pyessv.Node | None

    """
    authority = args[0]
    try:
        scope = args[1]
    except IndexError:
        scope = None
    try:
        collection = args[2]
    except IndexError:
        collection = None
    try:
        term = args[3]
    except IndexError:
        term = None

    names = [i.strip() for i in [authority, scope, collection, term] if i is not None]
    namespace = ":".join(names)

    return _load_by_namespace(namespace)


def _load_by_namespace(identifier):
    """Loads a vocabulary node from archive by trying to match it's namespace.

    :param str identifier: Vocabulary node namespace.

    :returns: First matching vocabulary node.
    :rtype: pyessv.Node | None

    """
    ns = str(identifier).split(':')
    assert len(ns) >= 1 and len(ns) <= 4, 'Invalid namespace'

    # Unpack.
    authority = scope = collection = term = None
    if len(ns) == 1:
        authority = ns[0]
    elif len(ns) == 2:
        authority, scope = ns
    elif len(ns) == 3:
        authority, scope, collection = ns
    elif len(ns) == 4:
        authority, scope, collection, term = ns

    # Walk nodes returning deepest match.
    for a in get_cached(Authority):
        if not _is_matched(a, authority):
            continue
        if scope is None:
            return a
        # ... scopes
        for s in a:
            if not _is_matched(s, scope):
                continue
            if collection is None:
                return s
            # ... collections
            for c in s:
                if not _is_matched(c, collection):
                    continue
                if term is None:
                    return c
                # ... terms (concrete)
                for t in c:
                    if _is_matched(t, term):
                        return t
                # ... terms (virtual)
                try:
                    c.apply_term_regex(term)
                except ValueError:
                    pass
                else:
                    return create_term(c, term)


def _load_by_uid(identifier):
    """Loads a vocabulary node from archive by trying to match it's unique identifier.

    :param str identifier: Vocabulary node unique identifier.

    :returns: First matching vocabulary node.
    :rtype: pyessv.Node | None

    """
    try:
        uuid.UUID(identifier)
    except ValueError:
        pass
    else:
        return get_cached(str(identifier))


def _is_matched(node, identifier):
    """Returns flag indicating whether node identifier is a match.

    """
    identifier = format_string(identifier).lower()

    # Matched by canonical name.
    if identifier == node.canonical_name:
        return True

    # Matched by raw name.
    if identifier == node.raw_name.lower():
        return True

    # Matched by uid.
    elif identifier == format_string(node.uid).lower():
        return True

    # Matched by synonyms.
    elif identifier in [format_string(i).lower() for i in node.synonyms]:
        return True

    # Matched by idx.
    if isinstance(node, Term):
        try:
            int(identifier)
        except ValueError:
            pass
        else:
            if int(identifier) == node.idx:
                return True

    return False


def add(authority):
    """Adds an authority to the archive.

    """
    cache(authority)


def save():
    """Persists archive to file system.

    """
    for authority in get_cached(Authority):
        write(authority)


def get_random_term(namespace):
    """Returns a random term.

    :param str namespace: Namespace of collection from which a term will be loaded.

    :returns: A random term's canonical name.
    :rtype: str

    """
    collection = load(namespace)
    if not collection:
        raise ValueError('Collection not found: {}'.format(namespace))

    if len(collection):
        return random.choice(collection).canonical_name

    return str(uuid.uuid4()).split('-')[0]
