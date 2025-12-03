//Script inspiré de: https://www.w3schools.com/howto/howto_js_copy_clipboard.asp
function CopierSQL() {
  var leSQL = document.getElementById('copiable');

  leSQL.select();
  leSQL.setSelectionRange(0, 9999);

  navigator.clipboard.writeText(leSQL.value);
}
