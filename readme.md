# 360 Giving data parser

A class for importing and using data in the [360 Giving](http://standard.threesixtygiving.org/en/latest/#) data standard
which is used to share data about grants made by grant-making
foundations.

The module particular relies on the [`flattentool`](https://github.com/OpenDataServices/flatten-tool) module, which
it uses to parse Excel and CSV files.

## Usage

To import the module use something like:

```python
from threesixty import ThreeSixtyGiving
```

You'll need to ensure the requirements from `requirements.txt` 
are installed first (`pip install -r requirements.txt`).

If you want to use the `to_pandas()` method you'll also need to install
[pandas](https://pandas.pydata.org/).

### As a class

```python
grants = {
    "grants": [
        {
            "id": "360G-KJD-001230",
            "title": "Grant award to Blue Trust",
            "description": "Towards respite day trips for young carers",
            "currency": "GBP",
            "amountAwarded": 5000,
            "awardDate": "2017-12-08T00:00:00+00:00",
            "recipientOrganization": [{"id": "GB-CHC-265374", "name": "Blue Trust"}],
            "fundingOrganization": [{"id": "GB-CHC-301077", "name": "K J D Foundation"}],
            "dateModified": "2017-12-22T00:00:00+00:00",
            "dataSource": "http://www.example.org/grants.htm"
        }
    ]
}
g = ThreeSixtyGiving(grants)
g.fetch_schema()

# see if there's any errors in the data
for e in g.get_errors():
    print(e)

# go through each grant
for grant in g:
    print(grant["title"]) # prints "Grant award to Blue Trust"
```

### Fetching data

The class has a number of methods for fetching data from files or URLs.

#### Import from a JSON file

```python
g = ThreeSixtyGiving.from_json("grants/ExampleTrust-grants.json")
# or:
g = ThreeSixtyGiving.from_file("grants/ExampleTrust-grants.json", "json")
```

The JSON file can also be a file object rather than a filename:

```python
with open("grants/ExampleTrust-grants.json") as f:
    g = ThreeSixtyGiving.from_json(f)
```

By default this method will check whether the file is valid against the
default schema. If you don't want to do this pass `validate=False`. 
If you want a different schema then pass `schema_url=https://url/to/schema.json`.

#### Import from an Excel file

```python
g = ThreeSixtyGiving.from_excel("grants/ExampleTrust-grants.xlsx")
# or:
g = ThreeSixtyGiving.from_file("grants/ExampleTrust-grants.xlsx", "xlsx")
```

By default this method will check whether the file is valid against the
default schema. If you don't want to do this pass `validate=False`. 
If you want a different schema then pass `schema_url=https://url/to/schema.json`.

#### Import from a CSV file

```python
g = ThreeSixtyGiving.from_csv("grants/ExampleTrust-grants.csv")
# or:
g = ThreeSixtyGiving.from_file("grants/ExampleTrust-grants.csv", "csv")
```

By default this method will check whether the file is valid against the
default schema. If you don't want to do this pass `validate=False`. 
If you want a different schema then pass `schema_url=https://url/to/schema.json`.

For a CSV file you can specify the encoding if needed, eg:

```python
g = ThreeSixtyGiving.from_csv("grants/ExampleTrust-grants.csv", encoding='latin1')
```

Otherwise it will attempt to guess the encoding.

#### Import from an URL

```python
g = ThreeSixtyGiving.from_url("http://example.org/opendata/ExampleTrust-grants.csv")
```

By default this method will check whether the file is valid against the
default schema. If you don't want to do this pass `validate=False`. 
If you want a different schema then pass `schema_url=https://url/to/schema.json`.

It will attempt to guess the filetype from the response, filetype can 
be manually specified by using the `filetype` attribute, e.g.:

```python
g = ThreeSixtyGiving.from_url("http://example.org/opendata/ExampleTrust-grants", filetype='csv')
```

### Checking data

Before the data is checked you'll need to ensure the data schema has been
fetched. This is done already if using `from_csv()`, `from_json()`, 
`from_excel()` or `from_url()` but needs to be done manually if just
creating the class directly with data:

```python
g = ThreeSixtyGiving(grants)
g.fetch_schema()
```

If you want to use a schema that is different from the default (<https://raw.githubusercontent.com/ThreeSixtyGiving/standard/master/schema/360-giving-package-schema.json>)
this needs to be specified using the `schema_url` parameter:

```python
g = ThreeSixtyGiving(
    grants,
    schema_url='http://example.org/360-giving-schema.json'
)
g.fetch_schema()
# or
g = ThreeSixtyGiving.from_json(
    "grants/ExampleTrust-grants.json",
    schema_url='http://example.org/360-giving-schema.json'
)
# or
g = ThreeSixtyGiving.from_csv(
    "grants/ExampleTrust-grants.csv",
    schema_url='http://example.org/360-giving-schema.json'
)
# or
g = ThreeSixtyGiving.from_excel(
    "grants/ExampleTrust-grants.xlsx",
    schema_url='http://example.org/360-giving-schema.json'
)
# or
g = ThreeSixtyGiving.from_url(
    "http://example.org/opendata/ExampleTrust-grants.csv",
    schema_url='http://example.org/360-giving-schema.json'
)
```

Currently the schema must be a URL pointing to a JSON file.

#### Check for errors

Once the schema has been fetched it's possible to validate data
against it. If the object already has grant data you can use `is_valid()`
to check whether the object is valid.

```python
g = ThreeSixtyGiving(grants)
g.fetch_schema()

if g.is_valid():
    print("Yay, it's a 360 Giving dataset")
else:
    print("Grants aren't valid")
```

If you have found errors you can see what they are:

```python
if not g.is_valid():
    for e in g.errors:
        print(e)
```

The output of `g.errors` is a list of [`jsonschema.exceptions.ValidationError`](https://python-jsonschema.readthedocs.io/en/latest/errors/#jsonschema.exceptions.ValidationError) objects. It's only available after `is_valid()` has been run. 

You can also iterate through `g.get_errors()` without checking for validity first.

### Use the data

If you're happy with the validity of the data you can use it. The `ThreeSixtyGiving`
object can be iterated to access the grants:

```python
g = ThreeSixtyGiving(grants)

for grant in g:
    print(grant) # prints '<Grant id="XXXXX">'
```

The iterable yields a `Grant` object, which works like a dictionary.

#### Send the data to a file

You can write the data to a file:

```python
g = ThreeSixtyGiving(grants)

g.to_json("grants.json")
g.to_csv("grants.csv")
g.to_excel("grants.xlsx")
```

The `to_csv()` and `to_excel()` methods can be passed the `convert_fieldnames`
parameter. If `convert_fieldnames` is True (which is the default) then
the returned files will have nicer looking fieldnames based on the title
for each field. So...

- `amountAwarded` becomes `Amount Awarded`
- `recipientOrganization.0.name` becomes `Recipient Org:0:Name`

Note that currently the `to_excel()` method returns an excel workbook with one
sheet in the flat file format, rather than a series of tabs like the `unflatten`
method in `flattentool`.

#### Get flat grants

The `to_flatfile()` method returns the data in a slightly different format.
It returns a tuple of `(data, fieldnames)`. `data` contains a list of all the
grants with any nested fields removed, so `{"recipientOrganization":[{"name": "Blue Trust"}]}` becomes `{"recipientOrganization.0.name": "Blue Trust"}`. This data is
suitable for writing to a flat file structure like CSV.

```python
g = ThreeSixtyGiving(grants)

data, fieldnames = g.to_flatfile()
for grant in data:
    print(grant["recipientOrganization.0.name"]) # prints "Blue Trust"
    print(grant["recipientOrganization"][0]["name"]) # raises KeyError
```

Note that the `to_flatfile()` method does not have a `convert_fieldnames` argument.

#### Get a pandas dataframe

The `to_pandas()` method returns a [pandas DataFrame](https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.html)
containing the grant data as a flat file.

The resulting data is based on the `to_flatfile()` method. The 
`convert_fieldnames` can be set to `False` to prevent user-friendly 
fieldnames being created.

This method will only work if the `pandas` library is installed, which
isn't part of `requirements.txt` so will need to be installed separately.

## Running tests

The test suite can be run through [pytest](https://docs.pytest.org/en/latest/):

```bash
py.test
```
