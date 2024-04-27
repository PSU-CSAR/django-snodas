"""
Basic idea here is any *.sql files in this dir will
be loaded as python modules where all queries in those
files will be python functions. The return type will be a
sql string that can be executed in a cursor.

The sql in the file should be python format string style (using {name}
for string interpolation), and can contain:

  - A 'module docstring' at the start of the file of the format:

      --=
      Here is the docstring.
      It can be multiline.
      It must be that the very beginning of the file.
      --=

  - Queries. Each query starts with a header, which should include
    the query name. All identifiers and parameters to be formatted
    must be explicitly declared in the header. All other lines of
    the header will be used as a docstring for the generated function.

    A query must end with a footer line like '--- endquery'.

    The format should look like this:

      --- name: query_name
      --- id: first
      --- param: first
      --- param: second
      --- These lines
      --- are used for the function docstring.
      <sql>
      --- endquery

      Note that a id and parameter of the same name will be filled
      with a single function arg of that name. But places where
      there is overlap, the identifier must end with '_i'.
"""

import os as _os
import re as _re
from glob import glob as _glob
from types import ModuleType as _MT

from psycopg2.sql import (
    SQL as _SQL,
)
from psycopg2.sql import (
    Identifier as _Identifier,
)
from psycopg2.sql import (
    Literal as _Literal,
)

# TODO: I think this might be refined if I used a custom
#       loader rather than the hacks below. Not sure.
#       https://docs.python.org/3/glossary.html#term-loader


class ParseError(ValueError):
    pass


class _QueriesFactory:
    _query_re = _re.compile(
        r'((?:---.*\n?)+)((?:(?!=^---).*?\n)+?)(?:(?:--- endquery.*$))',
        flags=_re.M,
    )
    _topdoc_re = _re.compile(r'(?:\A--=)(.*?)(?:^--=)', flags=_re.M | _re.S)
    _meta_replace_re = _re.compile(r'^---\s*')
    _name_re = _re.compile(r'(?:name:\s+)([\w\s]+)')
    _param_re = _re.compile(r'(?:param:\s+)(\w+)')
    _id_re = _re.compile(r'(?:id:\s+)(\w+)')
    _raw_re = _re.compile(r'(?:raw:\s+)(\w+)')

    def __init__(self, queries=None):
        if queries:
            for query in queries:
                self.add(*query)

    @staticmethod
    def _add(self, name, ids, params, raws, docstr, sql):
        if name in self.__dict__:
            raise ParseError(f"Duplicate query name: '{name}'")

        args = ', '.join(params.union(ids).union(raws))
        idstring = ', '.join([f'{i}_i=Ident({i})' for i in ids.intersection(params)])
        idstring += ', '.join([f'{i}=Ident({i})' for i in ids.difference(params)])
        rawstring = ', '.join([f'{r}=Raw(str({r}))' for r in raws])
        paramstring = ', '.join([f'{p}=Lit({p})' for p in params])
        func = 'def {name}({args}):\n    return sql.format({kwargs})\n'.format(
            name=name,
            args=args,
            kwargs=', '.join(filter(bool, [idstring, paramstring, rawstring])),
        )
        code = compile(func, '<string>', 'exec')
        eval(
            code,
            {
                'sql': sql,
                'Lit': _Literal,
                'Ident': _Identifier,
                'Raw': _SQL,
            },
            self.__dict__,
        )
        self.__dict__[name].__doc__ = docstr

    @classmethod
    def parse(cls, module, text, filepath=None):
        doc = cls._topdoc_re.match(text)
        queries = _MT(module, doc=(doc.group(1) if doc else None))
        _qs = cls._query_re.findall(text)
        if filepath:
            queries.__file__ = filepath
        for meta, sql in _qs:
            name, ids, params, raws, docstr = cls._extract_meta(meta)
            cls._add(queries, name, ids, params, raws, docstr, _SQL(sql))
        return queries

    @classmethod
    def _extract_meta(cls, meta_text):
        names = []
        params = set()
        ids = set()
        raws = set()
        docstr = ''

        for line in meta_text.split('\n'):
            line = cls._meta_replace_re.sub('', line)
            line = line.strip()

            is_name = cls._name_re.match(line)
            if is_name:
                names.append(is_name.group(1).replace(' ', '_'))
                continue

            is_param = cls._param_re.match(line)
            if is_param:
                param = is_param.group(1)
                if param in params:
                    raise ParseError(
                        f"Query parameter specified more than once: '{param}'"
                    )
                params.add(param)
                continue

            is_id = cls._id_re.match(line)
            if is_id:
                _id = is_id.group(1)
                if _id in ids:
                    raise ParseError(
                        f"Query identifier specified more than once: '{_id}'"
                    )
                ids.add(_id)
                continue

            is_raw = cls._raw_re.match(line)
            if is_raw:
                raw = is_raw.group(1)
                if raw in raws:
                    raise ParseError(
                        f"Query identifier specified more than once: '{_id}'"
                    )
                raws.add(raw)
                continue

            docstr += line + '\n'

        docstr = docstr[:-1]

        if len(names) > 1:
            raise ParseError(
                f"Query cannot have more than one name. Found '{names}'",
            )
        elif len(names) < 1:
            raise ParseError(
                'Unnamed query cannot be processed',
            )

        return names[0], ids, params, raws, docstr

    @classmethod
    def load(cls, query_file):
        name = _os.path.splitext(_os.path.basename(query_file))[0]
        with open(query_file) as f:
            return cls.parse(name, f.read(), filepath=query_file)

    @staticmethod
    def static():
        pass


locals().update(
    {
        _os.path.splitext(_os.path.basename(f))[0]: _QueriesFactory.load(f)
        for f in _glob(
            _os.path.join(_os.path.dirname(__file__), '*.sql'), recursive=False
        )
    }
)
