from clinv.sources.aws import Route53src
from unittest.mock import patch, call
import shutil
import tempfile
import unittest


class AWSBaseTestClass(object):
    '''
    Base class to setup the setUp and tearDown methods for the test cases.
    '''

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.inventory_dir = self.tmp
        self.boto_patch = patch('clinv.sources.aws.boto3', autospect=True)
        self.boto = self.boto_patch.start()
        self.logging_patch = patch('clinv.sources.aws.logging', autospect=True)
        self.logging = self.logging_patch.start()
        self.print_patch = patch('clinv.sources.aws.print', autospect=True)
        self.print = self.print_patch.start()

    def tearDown(self):
        self.boto_patch.stop()
        self.logging_patch.stop()
        self.print_patch.stop()
        shutil.rmtree(self.tmp)


class TestRoute53Source(AWSBaseTestClass, unittest.TestCase):
    '''
    Test the Route53 implementation in the inventory.
    '''

    def setUp(self):
        super().setUp()

        # Mock the source data fetch as it's on the __init__, this method is
        # tested on the TestRoute53SourceFetch class
        self.fetch_patch = patch(
            'clinv.sources.aws.Route53src._fetch_source_data', autospect=True
        )
        self.fetch = self.fetch_patch.start()

        # Initialize object to test
        user_data = {}
        self.src = Route53src(user_data)

        # Expected source_data dictionary generated by _fetch_source_data
        self.src.source_data = {
            'hosted_zones': [
                {
                    'Config': {
                        'Comment': 'This is the description',
                        'PrivateZone': False,
                    },
                    'Id': '/hostedzone/hosted_zone_id',
                    'Name': 'hostedzone.org',
                    'ResourceRecordSetCount': 1,
                    'records': [
                        {
                            'Name': 'record1.clinv.org',
                            'ResourceRecords': [
                                {
                                    'Value': '127.0.0.1'
                                },
                                {
                                    'Value': 'localhost'
                                },
                            ],
                            'TTL': 172800,
                            'Type': 'CNAME'
                        },
                    ],
                },
            ],
        }

    def tearDown(self):
        super().tearDown()
        self.fetch_patch.stop()

    def test_user_data_can_be_initialized(self):
        desired_user_data = {'a': 'b'}
        self.src = Route53src(desired_user_data)
        self.assertEqual(
            self.src.user_data,
            desired_user_data,
        )

    def test_generate_source_data_returns_expected_dictionary(self):
        self.assertEqual(
            self.src.generate_source_data(),
            self.src.source_data,
        )

    def test_fetch_user_data_creates_empty_user_data_if_no_source_data(self):
        self.src.source_data = {'hosted_zones': {}}
        self.src._fetch_user_data()
        self.assertEqual(self.src.user_data, {})

    def test_fetch_user_data_adds_desired_default_user_data(self):
        self.src._fetch_user_data()

        desired_default_user_data = {
            'hosted_zone_id-record1.clinv.org-cname': {
                'description': 'tbd',
                'to_destroy': 'tbd',
            },
        }
        self.assertEqual(
            self.src.user_data,
            desired_default_user_data,
        )

    def test_generate_user_data_returns_expected_dictionary(self):
        self.assertEqual(
            self.src.generate_user_data(),
            self.src.user_data,
        )

    def test_generate_inventory_return_empty_dict_if_no_data(self):
        self.src.source_data = {'hosted_zones': {}}
        self.assertEqual(self.src.generate_inventory(), {})

    def test_generate_inventory_creates_expected_dictionary(self):
        desired_inventory = {
            'hosted_zone_id-record1.clinv.org-cname': {
                'Name': 'record1.clinv.org',
                'ResourceRecords': [
                    {
                        'Value': '127.0.0.1'
                    },
                    {
                        'Value': 'localhost'
                    },
                ],
                'TTL': 172800,
                'Type': 'CNAME',
                'description': 'tbd',
                'to_destroy': 'tbd',
                'hosted_zone': {
                    'id': '/hostedzone/hosted_zone_id',
                    'private': False,
                    'name': 'hostedzone.org',
                },
                'state': 'active',
            },
        }

        self.assertEqual(self.src.generate_inventory(), desired_inventory)


class TestRoute53SourceFetch(AWSBaseTestClass, unittest.TestCase):
    '''
    Test the Route53 fetch implementation in the inventory.
    '''

    def setUp(self):
        super().setUp()

        # Initialize object to test
        user_data = {}
        self.src = Route53src(user_data)

        self.boto_client = self.boto.client.return_value

        # Expected boto call to get the hosted zones
        self.boto_client.list_hosted_zones.return_value = {
            'HostedZones': [
                {
                    'CallerReference': 'XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX',
                    'Config': {
                        'Comment': 'This is the description',
                        'PrivateZone': False,
                    },
                    'Id': '/hostedzone/hosted_zone_id',
                    'Name': 'hostedzone.org',
                    'ResourceRecordSetCount': 1
                },
            ],
            'IsTruncated': False,
            'MaxItems': '100',
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'content-length': '4211',
                    'content-type': 'text/xml',
                    'date': 'Mon, 15 Jul 2019 13:13:51 GMT',
                    'vary': 'accept-encoding',
                    'x-amzn-requestid': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
                },
                'HTTPStatusCode': 200,
                'RequestId': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
                'RetryAttempts': 0,
            },
        }

    def tearDown(self):
        super().tearDown()

    def test_fetch_source_data_creates_expected_source_data_attrib(self):
        # Expected boto call to get the resources of a hosted zone
        self.boto_client.list_resource_record_sets.return_value = {
            'IsTruncated': False,
            'MaxItems': '100',
            'ResourceRecordSets': [
                {
                    'Name': 'record1.clinv.org.',
                    'ResourceRecords': [
                        {
                            'Value': '127.0.0.1'
                        },
                        {
                            'Value': 'localhost'
                        },
                    ],
                    'TTL': 172800,
                    'Type': 'CNAME'
                },
            ],
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'content-length': '20952',
                    'content-type': 'text/xml',
                    'date': 'Mon, 15 Jul 2019 13:20:58 GMT',
                    'vary': 'accept-encoding',
                    'x-amzn-requestid': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
                },
                'HTTPStatusCode': 200,
                'RequestId': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
                'RetryAttempts': 0
            }
        }

        expected_source_data = {
            'hosted_zones': [
                {
                    'Config': {
                        'Comment': 'This is the description',
                        'PrivateZone': False,
                    },
                    'Id': '/hostedzone/hosted_zone_id',
                    'Name': 'hostedzone.org',
                    'ResourceRecordSetCount': 1,
                    'records': [
                        {
                            'Name': 'record1.clinv.org.',
                            'ResourceRecords': [
                                {
                                    'Value': '127.0.0.1'
                                },
                                {
                                    'Value': 'localhost'
                                },
                            ],
                            'TTL': 172800,
                            'Type': 'CNAME'
                        },
                    ],
                },
            ],
        }

        self.src._fetch_source_data(),
        self.assertEqual(
            self.src.source_data,
            expected_source_data,
        )

    def test_fetch_source_data_supports_pagination_on_resources(self):
        self.src.source_data = {'route53': {}}

        expected_first_list_resource_record_sets = {
            'IsTruncated': True,
            'NextRecordName': 'record2.clinv.org',
            'NextRecordType': 'CNAME',
            'MaxItems': '100',
            'ResourceRecordSets': [
                {
                    'Name': 'record1.clinv.org',
                    'ResourceRecords': [
                        {
                            'Value': '127.0.0.1'
                        },
                        {
                            'Value': 'localhost'
                        },
                    ],
                    'TTL': 172800,
                    'Type': 'CNAME'
                },
            ],
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'content-length': '20952',
                    'content-type': 'text/xml',
                    'date': 'Mon, 15 Jul 2019 13:20:58 GMT',
                    'vary': 'accept-encoding',
                    'x-amzn-requestid': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
                },
                'HTTPStatusCode': 200,
                'RequestId': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
                'RetryAttempts': 0
            }
        }
        expected_second_list_resource_record_sets = {
            'IsTruncated': False,
            'MaxItems': '100',
            'ResourceRecordSets': [
                {
                    'Name': 'record2.clinv.org',
                    'ResourceRecords': [
                        {
                            'Value': '127.0.0.1'
                        },
                        {
                            'Value': 'localhost'
                        },
                    ],
                    'TTL': 172800,
                    'Type': 'CNAME'
                },
            ],
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'content-length': '20952',
                    'content-type': 'text/xml',
                    'date': 'Mon, 15 Jul 2019 13:20:58 GMT',
                    'vary': 'accept-encoding',
                    'x-amzn-requestid': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
                },
                'HTTPStatusCode': 200,
                'RequestId': 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx',
                'RetryAttempts': 0
            }
        }

        self.boto.client.return_value.list_resource_record_sets.side_effect = [
                expected_first_list_resource_record_sets,
                expected_second_list_resource_record_sets,
        ]

        expected_source_data = {
            'hosted_zones': [
                {
                    'Config': {
                        'Comment': 'This is the description',
                        'PrivateZone': False,
                    },
                    'Id': '/hostedzone/hosted_zone_id',
                    'Name': 'hostedzone.org',
                    'ResourceRecordSetCount': 1,
                    'records': [
                        {
                            'Name': 'record1.clinv.org',
                            'ResourceRecords': [
                                {
                                    'Value': '127.0.0.1'
                                },
                                {
                                    'Value': 'localhost'
                                },
                            ],
                            'TTL': 172800,
                            'Type': 'CNAME'
                        },
                        {
                            'Name': 'record2.clinv.org',
                            'ResourceRecords': [
                                {
                                    'Value': '127.0.0.1'
                                },
                                {
                                    'Value': 'localhost'
                                },
                            ],
                            'TTL': 172800,
                            'Type': 'CNAME'
                        },
                    ],
                },
            ],
        }

        self.src._fetch_source_data()
        self.assertEqual(
            self.src.source_data,
            expected_source_data,
        )

        self.assertEqual(
            self.boto.client.return_value.list_resource_record_sets.mock_calls,
            [
                call(HostedZoneId='/hostedzone/hosted_zone_id'),
                call(
                    HostedZoneId='/hostedzone/hosted_zone_id',
                    StartRecordName='record2.clinv.org',
                    StartRecordType='CNAME'
                )
            ]
        )
