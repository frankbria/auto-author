"use strict";

var _react = require("@testing-library/react");
function Hello() {
  return /*#__PURE__*/React.createElement("h1", null, "Hello, world!");
}
test('renders hello text', function () {
  (0, _react.render)(/*#__PURE__*/React.createElement(Hello, null));
  expect(_react.screen.getByText(/hello/i)).toBeInTheDocument();
});
