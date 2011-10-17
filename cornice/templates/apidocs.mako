<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" xmlns:tal="http://xml.zope.org/namespaces/tal">
<head>
  <title>The Pyramid Web Application Development Framework</title>
  <meta http-equiv="Content-Type" content="text/html;charset=UTF-8"/>
  <meta name="keywords" content="python web application" />
  <meta name="description" content="pyramid web application" />
  <link rel="shortcut icon" href="${request.static_url('cornice:static/favicon.ico')}" />
  <link rel="stylesheet" href="${request.static_url('cornice:static/pylons.css')}" type="text/css" media="screen" charset="utf-8" />
  <link rel="stylesheet" href="${request.static_url('cornice:static/cornice.css')}" type="text/css" media="screen" charset="utf-8" />

  <link rel="stylesheet" href="http://static.pylonsproject.org/fonts/nobile/stylesheet.css" media="screen" />
  <link rel="stylesheet" href="http://static.pylonsproject.org/fonts/neuton/stylesheet.css" media="screen" />
  <!--[if lte IE 6]>
  <link rel="stylesheet" href="${request.static_url('cornice:static/ie6.css')}" type="text/css" media="screen" charset="utf-8" />
  <![endif]-->
</head>
<body>
    <div id="wrap">
        <div style="padding: 20px">
            <h2>Resources</h2>
            <hr/>
            %for api, value in routes:
        <div class="resource"> 
          <div class="resource-title"><h3>${api[1]} ${api[0]}</h3></div>
          <div class="resource-description">${util.rst2html(value['docstring']) | n}</div>
        </div>
        %endfor
       </div>
    </div>
  </div>
  <div id="footer">
    <div class="footer">&copy; Copyright 2008-2011, Mozilla Services</div>
  </div>
</body>
</html>
