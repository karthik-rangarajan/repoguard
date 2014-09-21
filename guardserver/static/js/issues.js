jQuery(function(){
    $.getJSON("/issues/?time=2", function(data){
        $.each(data, function(){
            var source = this["_source"];
            var false_positive = source["false_positive"] == "true" ? "Invalid": "Valid";
            var table_row = "<tr>" +
                "<td>" + source["repo_name"] + "</td>" +
                "<td>" + source["commit_id"] + "</td>" +
                "<td>" + source["matching_line"] + "</td>" +
                "<td>" + source["filename"] + "</td>" +
                "<td>" + source["description"] + "</td>" +
                "<td>" + source["last_reviewer"] + "</td>" +
                "<td>" + false_positive + "</td>" +
                "</tr>";
            $("#issue-body").append(table_row);
        })
    });
});