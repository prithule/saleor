import json
from unittest.mock import patch

import graphene
from django.shortcuts import reverse
from tests.utils import get_graphql_content

from saleor.graphql.core.mutations import (
    ModelFormMutation, ModelFormUpdateMutation)


def test_real_query(admin_client, product):
    product_attr = product.product_type.product_attributes.first()
    category = product.category
    attr_value = product_attr.values.first()
    filter_by = '%s:%s' % (product_attr.slug, attr_value.slug)
    query = '''
    query Root($categoryId: ID!, $sortBy: String, $first: Int, $attributesFilter: [AttributeScalar], $minPrice: Float, $maxPrice: Float) {
        category(id: $categoryId) {
            ...CategoryPageFragmentQuery
            __typename
        }
        attributes(inCategory: $categoryId) {
            edges {
                node {
                    ...ProductFiltersFragmentQuery
                    __typename
                }
            }
        }
    }

    fragment CategoryPageFragmentQuery on Category {
        id
        name
        url
        ancestors {
            edges {
                node {
                    name
                    id
                    url
                    __typename
                }
            }
        }
        children {
            edges {
                node {
                    name
                    id
                    url
                    slug
                    __typename
                }
            }
        }
        products(first: $first, sortBy: $sortBy, attributes: $attributesFilter, price_Gte: $minPrice, price_Lte: $maxPrice) {
            ...ProductListFragmentQuery
            __typename
        }
        __typename
    }

    fragment ProductListFragmentQuery on ProductCountableConnection {
        edges {
            node {
                ...ProductFragmentQuery
                __typename
            }
            __typename
        }
        pageInfo {
            hasNextPage
            __typename
        }
        __typename
    }

    fragment ProductFragmentQuery on Product {
        id
        name
        price {
            amount
            currency
            localized
            __typename
        }
        availability {
            ...ProductPriceFragmentQuery
            __typename
        }
        thumbnailUrl1x: thumbnailUrl(size: "255x255")
        thumbnailUrl2x: thumbnailUrl(size: "510x510")
        url
        __typename
    }

    fragment ProductPriceFragmentQuery on ProductAvailability {
        available
        discount {
            gross {
                amount
                currency
                __typename
            }
            __typename
        }
        priceRange {
            stop {
                gross {
                    amount
                    currency
                    localized
                    __typename
                }
                currency
                __typename
            }
            start {
                gross {
                    amount
                    currency
                    localized
                    __typename
                }
                currency
                __typename
            }
            __typename
        }
        __typename
    }

    fragment ProductFiltersFragmentQuery on ProductAttribute {
        id
        name
        slug
        values {
            id
            name
            slug
            color
            __typename
        }
        __typename
    }
    '''
    response = admin_client.post(
        reverse('api'), {
            'query': query,
            'variables': json.dumps(
                {
                    'categoryId': graphene.Node.to_global_id(
                        'Category', category.id),
                    'sortBy': 'name',
                    'first': 1,
                    'attributesFilter': [filter_by]})})
    content = get_graphql_content(response)
    assert 'errors' not in content


@patch('saleor.graphql.core.mutations.convert_form_fields')
@patch('saleor.graphql.core.mutations.convert_form_field')
def test_model_form_mutation(
        mocked_convert_form_field, mocked_convert_form_fields,
        model_form_class):

    mocked_convert_form_fields.return_value = {
        model_form_class._meta.fields: mocked_convert_form_field.return_value}

    class TestMutation(ModelFormMutation):
        test_field = graphene.String()

        class Arguments:
            test_input = graphene.String()

        class Meta:
            form_class = model_form_class
            return_field_name = 'test_return_field'

    meta = TestMutation._meta
    assert meta.form_class == model_form_class
    assert meta.model == 'test_model'
    assert meta.return_field_name == 'test_return_field'
    arguments = meta.arguments
    # check if declarative arguments are present
    assert 'test_input' in arguments
    # check if model form field is present
    mocked_convert_form_fields.assert_called_with(model_form_class, None)
    assert 'test_field' in arguments

    output_fields = meta.fields
    assert 'test_return_field' in output_fields
    assert 'errors' in output_fields


@patch('saleor.graphql.core.mutations')
def test_model_form_update_mutation(model_form_class):
    class TestUpdateMutation(ModelFormUpdateMutation):
        class Meta:
            form_class = model_form_class
            return_field_name = 'test_return_field'

    meta = TestUpdateMutation._meta
    assert 'id' in meta.arguments


def test_create_token_mutation(admin_client, staff_user):
    query = '''
    mutation {
        tokenCreate(email: "%(email)s", password: "%(password)s") {
            token
            errors {
                field
                message
            }
        }
    }
    '''
    success_query = query % {'email': staff_user.email, 'password': 'password'}
    response = admin_client.post(reverse('api'), {'query': success_query})
    content = get_graphql_content(response)
    assert 'errors' not in content
    token_data = content['data']['tokenCreate']
    assert token_data['token']
    assert not token_data['errors']

    error_query = query % {'email': staff_user.email, 'password': 'wat'}
    response = admin_client.post(reverse('api'), {'query': error_query})
    content = get_graphql_content(response)
    assert 'errors' not in content
    token_data = content['data']['tokenCreate']
    assert not token_data['token']
    errors = token_data['errors']
    assert errors
    assert not errors[0]['field']