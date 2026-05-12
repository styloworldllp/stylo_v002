const { get_conf } = require("../node_utils");

function get_url(socket, path) {
	const conf = get_conf();
	const port = conf.webserver_port || 8000;
	return `http://127.0.0.1:${port}${path}`;
}

module.exports = { get_url };
