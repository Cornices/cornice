Exhaustive list of the validations provided by cornice
######################################################

As you may have noticed, Cornice does some validation for you. This document
aims at documenting all those behaviours so you are not surprised if Cornice
does it for you without noticing.

Errors
======

When valitating contents, cornice will automatically throw a 400 error if the
data is invalid. Along with the 400 error, the body will contain a JSON dict
which can be parsed to know more about the problems ecountered.

Method not allowed
==================

In cornice, one path equals one service. If you call a path with the wrong
method, a `405 Method Not Allowed` error will be thrown (and not a 404), like
specified in the HTTP specification.

Authorization
=============

Authorization can be done using the `acl` parameter. If the authentication or
the authorization fails at this stage, a 401 or 403 error is returned,
depending the cases.

Content Types
=============

Each method can specify a list of content types it can handle. Per default,
`text/html` is assumed. In the case the client requests an invalid content
type, cornice will return a `406, Not Acceptable` with a list of available
content types for the particular URI and method.

Warning when returning JSON lists
=================================

JSON lists are subject to security threats, as defined
`in this document <http://bob.ippoli.to/archives/2007/04/05/fortify-javascript-hijacking-fud`.
In case you return a javascript list, a warning will be thrown. It will not
however prevent you from returning the array.

This behaviour can be disabled if needed (it can be removed from the list of
default filters)
