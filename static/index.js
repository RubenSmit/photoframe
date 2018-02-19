/* Javascript needed */

Validator = function() {
	this.time = function(input) {
		i = parseInt(input);
		if (i > 23)
			i = 23;
		if (i < 1 || isNaN(i))
			i = 0;
		return i.toString();
	}

	this.delay = function(input) {
		i = parseInt(input);
		if (i < 30 || isNaN(i))
			i = 30;
		return i.toString();
	}

	this.refresh = function(input) {
		i = parseInt(input);
		if (i < 1 || isNaN(i))
			i = 1;
		return i.toString();
	}


	this.depth = function(input) {
		i = parseInt(input);
		if (isNaN(i) || [8, 16, 24, 32].indexOf(i) == -1)
			i = 8;
		return i.toString();
	}

	this.width = function(input) {
		i = parseInt(input);
		if (i < 640 || isNaN(i))
			i = 640;
		return i.toString();
	}

	this.height = function(input) {
		i = parseInt(input);
		if (i < 480 || isNaN(i))
			i = 480;
		return i.toString();
	}
}

function populateKeywords() {
	$.ajax({
		url:"/keywords",
		type:"GET",
		contentType: "application/json; charset=utf-8",
		dataType: "json"
	}).done(function(data){
		$("#keywords").empty();
		for (entry in data['keywords']) {
			$('#keywords').append('<input class="delete" type="button" data-id="' + entry + '" value="Delete"><input class="search" data-key="' + encodeURIComponent(data["keywords"][entry]) + '" type="button" value="Open"> ');
			if (data["keywords"][entry] == "")
				$('#keywords').append("&lt;empty - picks one of the last photos added&gt;");
			else
				$('#keywords').append(data["keywords"][entry]);
			$('#keywords').append('<br>');
		}
		$("input[class='search']").click(function(){
			window.open("https://photos.google.com/search/" + $(this).data('key'), "_blank");
		});
		$("input[class='delete']").click(function(){
			if (confirm("Are you sure?")) {
				$.ajax({
					url:"/keywords/delete",
					type:"POST",
					data: JSON.stringify({ id: $(this).data('id') }),
					contentType: "application/json; charset=utf-8",
					dataType: "json"
				}).done(function(data){
					populateKeywords();
				});
			}
		});
	});

	$('#test').click(function(){
		var key = $('#keyword').val().trim()
		if (key != "")
			window.open("https://photos.google.com/search/" + encodeURIComponent(key), "_blank");
		else
			window.open("https://photos.google.com/", "_blank");
	});

	$('#add').click(function(){
		$.ajax({
			url:"/keywords/add",
			type:"POST",
			data: JSON.stringify({ keywords: $('#keyword').val() }),
			contentType: "application/json; charset=utf-8",
			dataType: "json"
		}).done(function(data){
			if (data['status']) {
				populateKeywords();
				$('#keyword').val("");
			}
		});
	});
}

function loadSettings(funcOk)
{
	$.ajax({
		url:"/setting"
	}).done(function(data){
		result = {}
		for (key in data) {
			if (key == 'keywords')
				continue;
			value = data[key];
			result[key] = value;
		}
		funcOk(result);
	});
}

function checkOAuth(funcOk, funcErr) {
	$.ajax({
		url:"/has/oauth"
	}).done(function(data){
		if (data['result']) {
			funcOk();
		} else {
			funcErr();
		}
	});
}

function checkLink(funcOk, funcErr) {
	$.ajax({
		url:"/has/token"
	}).done(function(data){
		if (data["result"]) {
			funcOk();
		} else
			funcErr();
	});
}

function getVersion(commit, date) {
	$.ajax({
		url:"/details/version"
	}).done(function(data){
		if (commit != null)
			$(commit).text(data["commit"]);
		if (date != null)
			$(date).text(data["date"]);
	});
}

TemplateEngine = function() {
	this.regTemplate = {}

	this.loadTemplate= function(templates, i, funcDone) {
		url = templates[i++];
		thiz = this;

		$.ajax({
			url:'template/' + url
		}).done(function(data){
			thiz.regTemplate[url] = Handlebars.compile(data);
			if (i == templates.length)
				funcDone();
			else
				thiz.loadTemplate(templates, i, funcDone);
		})
	}

	this.load = function(templates, funcDone) {
		this.loadTemplate(templates, 0, funcDone);
	}

	this.get = function(url) {
		return this.regTemplate[url];
	}
}