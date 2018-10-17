import tempfile
import os

import pytest
import requests_mock
import pandas

from threesixty import ThreeSixtyGiving, Grant

@pytest.fixture
def get_file():
    thisdir = os.path.dirname(os.path.realpath(__file__))
    return lambda x: os.path.join(thisdir, x)

@pytest.fixture
def m():
    urls = [
        ("sample_data/360-giving-package-schema.json",
         'https://raw.githubusercontent.com/ThreeSixtyGiving/standard/master/schema/360-giving-package-schema.json'),
        ('sample_data/360-giving-schema.json',
         'https://raw.githubusercontent.com/ThreeSixtyGiving/standard/master/schema/360-giving-schema.json'),
    ]
    m = requests_mock.Mocker()
    thisdir = os.path.dirname(os.path.realpath(__file__))
    for i in urls:
        with open(os.path.join(thisdir, i[0]), 'rb') as f_:
            m.get(i[1], content=f_.read())
    m.start()
    return m


def test_json(get_file, m):
    g = ThreeSixtyGiving.from_json(
        get_file("sample_data/ExampleTrust-grants-fixed.json"))
    assert g.is_valid()

    # @TODO: add test for invalid JSON


def test_csv(get_file, m):
    g = ThreeSixtyGiving.from_csv(
        get_file("sample_data/ExampleTrust-grants-fixed.csv"))
    assert g.is_valid()

    with pytest.raises(ValueError):
        g = ThreeSixtyGiving.from_csv(
            get_file("sample_data/ExampleTrust-grants-broken.csv"))


def test_excel(get_file, m):
    g = ThreeSixtyGiving.from_excel(
        get_file("sample_data/ExampleTrust-grants-fixed.xlsx"))
    assert g.is_valid()

    with pytest.raises(ValueError):
        g = ThreeSixtyGiving.from_excel(
            get_file("sample_data/ExampleTrust-grants-broken.xlsx"))


def test_url(get_file, m):
    test_files = [
        "sample_data/ExampleTrust-grants-fixed.xlsx",
        "sample_data/ExampleTrust-grants-broken.xlsx",
        "sample_data/ExampleTrust-grants-fixed.csv",
        "sample_data/ExampleTrust-grants-broken.csv",
        "sample_data/ExampleTrust-grants-fixed.json",
    ]
    for f in test_files:
        with open(get_file(f), 'rb') as f_:
            url = 'http://example.com/{}'.format(f)
            contents = f_.read()
            m.register_uri('GET', url, content=contents)

            if "broken" in f:
                with pytest.raises(ValueError):
                    g = ThreeSixtyGiving.from_url(url)
            else:
                g = ThreeSixtyGiving.from_url(url)
                assert g.is_valid()

                # test content-disposition header
                content_disposition_url = url.replace(
                    "ExampleTrust-grants", "ContentDisposition")
                m.register_uri(
                    'GET',
                    content_disposition_url,
                    content=contents,
                    headers={
                        "Content-Disposition": 'attachment; filename="{}"'.format(
                            url.replace("http://example.com/sample_data/ExampleTrust-grants", "file-")
                        )
                    }
                )
                g = ThreeSixtyGiving.from_url(content_disposition_url)
                assert g.is_valid()


def test_output(get_file, m):
    g = ThreeSixtyGiving.from_file(
        get_file("sample_data/ExampleTrust-grants-fixed.xlsx"), "xlsx")
    grants = list(g)
    assert len(grants) == 10
    assert isinstance(grants[0], Grant)
    assert grants[2].id == '360G-KJD-001232'


def test_pandas_output(get_file, m):
    g = ThreeSixtyGiving.from_file(
        get_file("sample_data/ExampleTrust-grants-fixed.xlsx"), "xlsx")
    df = g.to_pandas()

    assert isinstance(g.to_pandas(), pandas.DataFrame)
    assert df.columns.all(['Identifier', 'Title', 'Description', 'Currency', 'Amount Awarded',
                           'Award Date', 'Recipient Org:0:Identifier', 'Recipient Org:0:Name',
                           'Beneficiary Location:0:Name', 'Beneficiary Location:0:Country Code',
                           'Beneficiary Location:0:Geographic Code',
                           'Beneficiary Location:0:Geographic Code Type',
                           'Funding Org:0:Identifier', 'Funding Org:0:Name', 'Last Modified',
                           'Data Source'])

    df = g.to_pandas(convert_fieldnames=False)
    assert df.columns.all(['id', 'title', 'description', 'currency', 'amountAwarded', 'awardDate',
                           'recipientOrganization.0.id', 'recipientOrganization.0.name',
                           'beneficiaryLocation.0.name', 'beneficiaryLocation.0.countryCode',
                           'beneficiaryLocation.0.geoCode', 'beneficiaryLocation.0.geoCodeType',
                           'fundingOrganization.0.id', 'fundingOrganization.0.name',
                           'dateModified', 'dataSource'])


def test_excel_output(get_file, m):
    t_, t = tempfile.mkstemp(suffix='.xlsx')
    os.close(t_)
    g = ThreeSixtyGiving.from_file(
        get_file("sample_data/ExampleTrust-grants-fixed.xlsx"), "xlsx")
    g.to_excel(t)

    h = ThreeSixtyGiving.from_excel(t)
    assert h.is_valid()


def test_json_output(get_file, m):
    t_, t = tempfile.mkstemp(suffix='.json')
    os.close(t_)
    g = ThreeSixtyGiving.from_file(
        get_file("sample_data/ExampleTrust-grants-fixed.xlsx"), "xlsx")
    g.to_json(t)

    h = ThreeSixtyGiving.from_json(t)
    assert h.is_valid()


def test_csv_output(get_file, m):
    t_, t = tempfile.mkstemp(suffix='.csv')
    os.close(t_)
    g = ThreeSixtyGiving.from_file(
        get_file("sample_data/ExampleTrust-grants-fixed.json"), "json")
    g.to_csv(t)

    h = ThreeSixtyGiving.from_csv(t)
    assert h.is_valid()
