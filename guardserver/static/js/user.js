jQuery(function(){
        server = localStorage.getItem("server");
        $.getJSON(server + "/current_user", function(data){
            current_name = data.name;
            $("#current-user").append(current_name);
            localStorage.setItem("current_user", current_name);
        });
});
