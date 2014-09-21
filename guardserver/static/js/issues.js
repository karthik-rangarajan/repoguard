jQuery(function(){
    $.getJSON("/issues/?time=7", function(data){
        add_issues_to_table(data, "#issue-body-all");
    });

    $.getJSON("/issues/?time=7&false_positive=false", function(data){
        add_issues_to_table(data, "#issue-body-valid");
    });
});

function add_issues_to_table(data, dom_element) {
    $.each(data, function(){
        var source = this["_source"];
        var false_positive = source["false_positive"] == "true" ? "Invalid": "Valid";
        var table_row = "<tr>" +
            "<td>" + source["repo_name"] + "</td>" +
            "<td>" + source["commit_id"] + "</td>" +
            "<td>" + $("<div />").text(source["matching_line"]).html() + "</td>" +
            "<td>" + source["filename"] + "</td>" +
            "<td>" + source["description"] + "</td>" +
            "<td>" + source["last_reviewer"] + "</td>" +
            "<td>" + false_positive + "</td>" +
            "</tr>";
        $(dom_element).prepend(table_row);
    });
}