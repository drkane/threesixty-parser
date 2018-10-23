import json
import tempfile
import os
import shutil
import csv
import re
from collections import OrderedDict

import flattentool
import requests
from jsonref import JsonRef
from jsonschema import Draft4Validator, FormatChecker

ENCODINGS_TO_CHECK = ['utf-8-sig', 'cp1252', 'latin_1']
CONTENT_TYPE_MAP = {
    'application/json': 'json',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
    'text/csv': 'csv'
}

class ThreeSixtyGiving:

    root_id = 'grants'
    schema_url = 'https://raw.githubusercontent.com/ThreeSixtyGiving/standard/master/schema/360-giving-package-schema.json'
    user_agent = '360Giving data'

    def __init__(self, data=None, schema_url=None, schema=None):
        self.schema = None
        self.validator = None
        self.replace_names = OrderedDict()

        if schema_url:
            self.schema_url = schema_url
            # @TODO: should this actually fetch the schema at this point?
            # eg:
            # if schema or schema_url:
            #   self.fetch_schema(schema=schema, schema_url=schema_url)
        if schema:
            self.fetch_schema(schema=schema)

        self.errors = []
        self.valid = None
        if data:
            self.data = data
        else:
            self.data = {}

    def __iter__(self):
        """
        Iterating the object yields grant objects for each of the loaded grants
        """
        for g in self.data.get(self.root_id, []):
            yield Grant(**g)

    @classmethod
    def from_url(cls, url, filetype=None, **kwargs):
        """
        Fetches a 360Giving format file from an URL (using requests),
        guesses the filetype if not given, and then parses the file
        """

        # Attempt to fetch the file
        r = requests.get(url, headers={'User-Agent': cls.user_agent})
        r.raise_for_status()

        # work out the filetype if not given
        if not filetype:
            content_type = r.headers.get('content-type', '').split(';')[0].lower()
            if content_type and content_type in CONTENT_TYPE_MAP:
                filetype = CONTENT_TYPE_MAP[content_type]
            elif 'content-disposition' in r.headers:
                d = r.headers['content-disposition']
                filetype = re.search('filename=(.+)', d)
                if filetype:
                    filetype = filetype[0].split('.')[-1].strip('"')
            else:
                filetype = url.split('.')[-1]
            if filetype not in CONTENT_TYPE_MAP.values():
                raise ValueError("Unrecognised file type [{}]".format(filetype))

        # write the content to a temporary file
        t_, t = tempfile.mkstemp(suffix='.{}'.format(filetype))
        os.write(t_, r.content)
        os.close(t_)
        c = cls.from_file(t, filetype, **kwargs)
        os.remove(t)
        return c

    @classmethod
    def from_file(cls, f, filetype, **kwargs):
        """
        Opens a 360Giving file and returns an object containing the data

        Wrapper for individual filetype methods

        :param f: file path to be opened. JSON files can also be passed as `fileobj` items
        :param filetype: The type of file to be opened (one of ['csv', 'json', 'excel'])
        :return: Object of this class with data loaded

        Additional keyword arguments are passed to the opening methods

        @TODO: make `filetype` optional and guess the filetype if not given
        """

        if filetype == 'json':
            return cls.from_json(f, **kwargs)
        elif filetype == 'csv':
            return cls.from_csv(f, **kwargs)
        elif filetype in ['xlsx', 'xls', 'excel']:
            return cls.from_excel(f, **kwargs)

    @classmethod
    def from_csv(cls, f, encoding=None, **kwargs):
        """
        Opens a CSV format 360Giving file, and return an object for accessing the data

        :param str f: file path to be opened
        :param str encoding: will be passed to open(), will be guessed if not given
        :return: Object of this class with data loaded

        Additional keyword arguments are passed to `cls.to_json()` which is used to parse the converted file

        @TODO: better version of unflatten which allows for returning the data not a temporary file
        """

        # `flattentool.unflatten` is designed to accept a directory of CSV files
        # so need to create a dummy directory
        tmp_dir = tempfile.mkdtemp()
        destination = os.path.join(tmp_dir, 'grants.csv')
        shutil.copy(f, destination)
        encoding = cls.guess_encoding(destination) if not encoding else encoding

        json_file, json_output = tempfile.mkstemp(suffix='.json')
        os.close(json_file)
        flattentool.unflatten(
            tmp_dir,
            output_name=json_output,
            input_format="csv",
            root_list_path=cls.root_id,
            root_id='',
            # @TODO: Need to better handle the schema here - there's duplication with the flattentool also fetching it
            schema='https://raw.githubusercontent.com/ThreeSixtyGiving/standard/master/schema/360-giving-schema.json',
            convert_titles=True,
            encoding=encoding,
            # I don't think this is used properly here
            metatab_schema=cls.schema_url,
            metatab_name='Meta',
            metatab_vertical_orientation=True,
        )
        c = cls.from_json(json_output, **kwargs)
        os.remove(json_output)
        return c

    @classmethod
    def from_excel(cls, f, **kwargs):
        """
        Opens an Excel format 360Giving file, and return an object for accessing the data

        :param str f: file path to an Excel file
        :return: Object of this class with data loaded

        Additional keyword arguments are passed to `cls.to_json()` which is used to parse the converted file

        @TODO: better version of unflatten which allows for returning the data not a temporary file
        """
        json_file, json_output = tempfile.mkstemp(suffix='.json')
        os.close(json_file)
        flattentool.unflatten(
            f,
            output_name=json_output,
            input_format="xlsx",
            root_list_path=cls.root_id,
            root_id='',
            # @TODO: Need to better handle the schema here - there's duplication with the flattentool also fetching it
            schema='https://raw.githubusercontent.com/ThreeSixtyGiving/standard/master/schema/360-giving-schema.json',
            convert_titles=True,
            # I don't think this is used properly here
            metatab_schema=cls.schema_url,
            metatab_name='Meta',
            metatab_vertical_orientation=True,
        )
        c = cls.from_json(json_output, **kwargs)
        os.remove(json_output)
        return c

    from_xlsx = from_excel  # alias for to_excel

    @classmethod
    def from_json(cls, f, validate=True, **kwargs):
        """
        Opens a json format 360Giving file, and return an object for accessing the data

        :param str f: file path to an json file or a file-like object with a `read()` method
        :param bool validate: Whether to validate the file after the data is loaded
        :return: Object of this class with data loaded

        Additional keyword arguments are passed to `cls.__init__()` to produce the data
        """
        opened_file = False
        if isinstance(f, str):
            fileobj = open(f)
            opened_file = True
        else:
            fileobj = f
        c = cls(json.load(fileobj), **kwargs)
        if opened_file:
            fileobj.close()
        if validate:
            c.fetch_schema()
            if not c.is_valid():
                raise ValueError("Invalid file") # @TODO: better error messages here
        return c

    @classmethod
    def guess_encoding(cls, f, encodings=None):
        """
        Given a file will try to work out the encoding, based on running through
        a list of encodings and seeing whether any UnicodeDecodeErrors occur.

        :param str f: path of the file to test
        :param list(str) encodings: list of encodings to test
        :return: Best guess at the file encoding
        :rtype: str

        @TODO: Could be more efficient by just opening the first part of the file
        """
        if encodings is None:
            encodings = ENCODINGS_TO_CHECK

        for e in encodings:
            try:
                with open(f, encoding=e) as encoding_file:
                    encoding_file.read()
            except UnicodeDecodeError:
                continue
            else:
                return e
        return None

    def fetch_schema(self, schema_url=None, schema=None):
        """
        Fetch a schema based on the value in self.schema_url.

        As well as fetching the initial schema file, the function will also:
         - replace any references in the schema with the actual definitions (using JsonRed)
         - use `jsonschema` to create a validator that can be used to check documents against the schema
         - create a dictionary of field name conversions (as regex) that can be used to replace field names with more user friendly ones

        The order of preference for loading a schema is:

        1. A schema object given as a parameter to this method
        2. A schema object already provided to this object
        3. A schema fetched from schema_url provided to this method
        4. A schema fetched from the schema_url provided to this object

        :param str schema_url: URL of a JSON schema
        :param dict schema: dictionary containing a JSON schema
        :return: The full schema
        """

        # if no schema_url given then use the default one
        if schema_url is None:
            schema_url = self.schema_url

        # if no schema is given or present already then load from URL
        if self.schema is None and schema is None:
            self.schema = requests.get(schema_url).json()

        # else if a schema has been given then use that one
        elif schema is not None:
            self.schema = schema

        if self.schema is None:
            raise ValueError("No schema found")

        # fetch the whole schema including references
        self.schema = JsonRef.replace_refs(self.schema)

        # create a validator
        self.validator = Draft4Validator(
            self.schema, format_checker=FormatChecker())

        # recursively find property names and titles
        def recurse_names(props, replace_names=OrderedDict(), prefix_k='', prefix_v=''):
            for i, prop in props.items():
                name_k = '{}.([0-9]+).{}'.format(prefix_k, i) if prefix_k != '' else i
                name_v = '{}:\\1:{}'.format(prefix_v, prop.get(
                    "title", i)) if prefix_v != '' else prop.get("title", i)
                if prop.get("type") == 'array':
                    replace_names = recurse_names(
                        prop.get("items", {}).get("properties", {}),
                        replace_names,
                        name_k,
                        name_v
                    )
                else:
                    replace_names[name_k] = name_v
            return replace_names

        self.replace_names = recurse_names(
            self.schema['properties'][self.root_id]['items']['properties'],
            self.replace_names
        )

        return self.schema


    def get_errors(self, data=None):
        """
        Using the schema and validator created by `fetch_schema`, validate
        a dataset and yield any errors that result

        :param dict data: Data to check for errors
        :return: Iterator of any errors found in the data
        """
        # if no schema given then we can't error check
        if self.schema is None or self.validator is None:
            raise ValueError("No schema available to check")

        if data is None:
            data = self.data

        for e in self.validator.iter_errors(data):
            # ignore error where the datetime value is one of a type
            if e.validator == 'oneOf' and e.validator_value[0] == {'format': 'date-time'}:
                continue
            yield e

    def is_valid(self):
        """
        Check whether the current object has a valid file against the schema

        :return: True|False whether the file is valid or not. Returns None if validity hasn't been checked (eg not data)
        :rtype: bool or None
        """
        if self.valid is None and self.data:
            self.errors = list(self.get_errors(self.data))
            self.valid = len(self.errors) == 0

        return self.valid

    def to_json(self, f):
        """
        Convert data into a JSON file

        :param f: Either a file path or an open fileobj. If a fileobj is provided it won't close it afterwards
        """
        closefile = False
        if isinstance(f, str):
            f = open(f, 'w')
            closefile = True
        json.dump(self.data, f, indent=4, ensure_ascii=False)
        if closefile:
            f.close()

    def to_flatfile(self):
        """
        Turn the object stored in the data into a "flat" list of dicts

        The dicts will have keys that represent the path to the value
        in the nested object (eg grants['recipientOrganization'][0]['name']
        is turned into `recipientOrganization.0.name`)

        :return: A tuple with the flattened data and the fieldnames within the data
        :rtype: tuple
        """
        data = []
        fieldnames = []
        for g in self:
            g_flat = g.to_flat()
            data.append(g_flat)
            for f in g_flat.keys():
                if f not in fieldnames:
                    fieldnames.append(f)
        return (data, fieldnames)

    def to_csv(self, f, convert_fieldnames=True):
        """
        Convert data into a CSV file

        :param f: Either a file path or an open fileobj
        :param bool convert_fieldnames: Whether to convert fieldnames into a more friendly format or not (uses the dictionary created in `self.fetch_schema()`)

        Note: closes the file after writing the data
        """
        closefile = False
        if isinstance(f, str):
            f = open(f, 'w')
            closefile = True

        data, fieldnames = self.to_flatfile()

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if convert_fieldnames:
            writer.writerow(self.convert_fieldnames(fieldnames))
        else:
            writer.writeheader()
        for r in data:
            writer.writerow(r)
        if closefile:
            f.close()

    def to_excel(self, f, multiple_sheets=False, convert_fieldnames=True):
        """
        Convert data into an Excel file

        :param f: file path for excel file
        :param bool multiple_sheets: Whether the output will be all on one sheet, or with one sheet for each sub-category
        :param bool convert_fieldnames: Whether to convert fieldnames into a more friendly format or not (uses the dictionary created in `self.fetch_schema()`)

        Note: closes the file after writing the data
        """
        import xlsxwriter

        if multiple_sheets:
            raise NotImplementedError("Not yet able to do multiple sheets")
        else:

            data, fieldnames = self.to_flatfile()

            workbook = xlsxwriter.Workbook(f)
            worksheet = workbook.add_worksheet()

            # write header
            if convert_fieldnames:
                worksheet.write_row(0, 0, self.convert_fieldnames(fieldnames).values())
            else:
                worksheet.write_row(0, 0, fieldnames)

            # write rows
            for row, r in enumerate(data):
                worksheet.write_row(row+1, 0, [r.get(f) for f in fieldnames])
            workbook.close()

    to_xlsx = to_excel # alias for to_excel

    def to_pandas(self, convert_fieldnames=True):
        """
        Convert the data to a pandas DataFrame.

        :param bool convert_fieldnames: Whether to convert fieldnames into a more friendly format or not (uses the dictionary created in `self.fetch_schema()`)
        :return: Pandas dataframe
        :raises: ImportError if pandas is not installed
        """
        import pandas
        data, fieldnames = self.to_flatfile()
        df = pandas.DataFrame(data)
        if convert_fieldnames:
            df = df.rename(columns=self.convert_fieldnames(fieldnames))

        return df

    def convert_fieldnames(self, fieldnames):
        """
        Applies the transformations in `self.replace_names` to a set of fieldnames

        :param list[str] fieldnames: A list of fieldnames to replace
        :return: Dictionary of old:new values for fieldnames
        """
        fieldnames = OrderedDict(zip(fieldnames, fieldnames))
        for old, new in self.replace_names.items():
            for field in fieldnames:
                if re.fullmatch(old, field):
                    fieldnames[field] = re.sub(old, new, field)
        return fieldnames


class Grant:
    """
    A class to hold details about a particular grant in the 360Giving standard
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return '<Grant {}>'.format(self.id)

    def to_flat(self):
        """
        Turn the nested grant object into a flat dictionary of key:values

        Nested fields are turned into the form `key.0.subkey`
        """
        def flatten(vals, prefix=''):
            new_vals = []
            if isinstance(vals, list):
                vals = dict(zip(map(str, range(len(vals))), vals))

            for v in vals:
                new_key = '{}.{}'.format(prefix, v) if prefix != '' else v
                if isinstance(vals[v], list):
                    new_vals.extend(flatten(vals[v], new_key))
                elif isinstance(vals[v], dict):
                    new_vals.extend(flatten(vals[v], new_key))
                else:
                    new_vals.append((new_key, vals[v]))
            return new_vals

        return OrderedDict(flatten(self.__dict__))
