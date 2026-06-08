

window.addEventListener("load", function(){

    const role = localStorage.getItem("user_role");
    const user_id = localStorage.getItem("user_id");

    if (!user_id) return;

    window.updateUnread = function(){

        let url = "";

        if(role === "Student"){
            url = `${api}/student/${user_id}/unread_count`;
        } else if(role === "Instructor"){
            url = `${api}/instructor/${user_id}/unread_count`;
        }

        fetch(url)
        .then(res => res.json())
        .then(data => {

            const badge = document.getElementById("notifBadge");
            if(!badge) return;

            badge.innerText = data.unread > 0 ? data.unread : "";
        });
    }

    updateUnread();
    setInterval(updateUnread, 5000);
});