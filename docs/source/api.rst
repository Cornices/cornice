Cornice API
###########

Service
=======

.. py:module:: cornice.service

This document describes the methods proposed by cornice. It is
automatically generated from the source code.

.. autoclass:: cornice.service.Service
.. autofunction:: cornice.service.decorate_view


Resource
========

.. autofunction:: cornice.resource.resource
.. autofunction:: cornice.resource.view
.. autofunction:: cornice.resource.add_view
.. autofunction:: cornice.resource.add_resource


Validation
==========

.. autofunction:: cornice.validators.extract_cstruct
.. autofunction:: cornice.validators.colander_body_validator
.. autofunction:: cornice.validators.colander_headers_validator
.. autofunction:: cornice.validators.colander_path_validator
.. autofunction:: cornice.validators.colander_querystring_validator
.. autofunction:: cornice.validators.colander_validator
.. autofunction:: cornice.validators.marshmallow_body_validator
.. autofunction:: cornice.validators.marshmallow_headers_validator
.. autofunction:: cornice.validators.marshmallow_path_validator
.. autofunction:: cornice.validators.marshmallow_querystring_validator
.. autofunction:: cornice.validators.marshmallow_validator

Errors
======

.. autoclass:: cornice.errors.Errors
