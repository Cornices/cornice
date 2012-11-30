Exhaustive list of the validations provided by cornice
######################################################

As you may have noticed, Cornice does some validation for you. This document
aims at documenting all those behaviours so you are not surprised if Cornice
does it for you without noticing.

Errors
======

When validating contents, cornice will automatically throw a 400 error if the
data is invalid. Along with the 400 error, the body will contain a JSON dict
which can be parsed to know more about the problems encountered.

Method not allowed
==================

In cornice, one path equals one service. If you call a path with the wrong
method, a `405 Method Not Allowed` error will be thrown (and not a 404), like
specified in the HTTP specification.

Authorization
=============

Authorization can be done using the `acl` parameter. If the authentication or
the authorization fails at this stage, a 401 or 403 error is returned,
depending on the cases.

Content Types (ingress)
=======================

Each method can specify a list of content types it can receive. Per default,
any content type is allowed. In the case the client sends a request with an
invalid `Content-Type` header, cornice will return a
`415 Unsupported Media Type` with an error message containing the list of
valid request content types for the particular URI and method.

Content Types (egress)
======================

Each method can specify a list of content types it can respond with.
Per default, `text/html` is assumed. In the case the client requests an
invalid content type via `Accept` header, cornice will return a
`406 Not Acceptable` with an error message containing the list of available
response content types for the particular URI and method.

Warning when returning JSON lists
=================================

JSON lists are subject to security threats, as defined
`in this document <http://haacked.com/archive/2009/06/25/json-hijacking.aspx>`_.
In case you return a javascript list, a warning will be thrown. It will not
however prevent you from returning the array.

This behaviour can be disabled if needed (it can be removed from the list of
default filters)
